# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""Integration tests for single-port serving: SPA fallback, API isolation, and run.py CLI."""

import argparse
import os
import sys
import tempfile
import unittest
from pathlib import Path

from unittest.mock import MagicMock, patch

from backend.app.compat import HTTPException, Session, TestClient, create_engine
from backend.app.database import init_db
from backend.app.main import ASSETS_DIR, DIST_DIR, DIST_INDEX, app, serve_root, serve_spa


class TestRootRoute(unittest.TestCase):
    """Verify that GET / returns HTTP 200 in all modes (frontend built or not)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_server.db")
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        init_db(self.engine)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_root_returns_200(self) -> None:
        """GET / must always return 200 regardless of whether the frontend is built."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_root_response_contains_app_info_when_no_dist(self) -> None:
        """When frontend/dist/index.html is absent, GET / returns a JSON hint."""
        with patch("backend.app.main.DIST_INDEX") as mock_dist_index:
            mock_dist_index.exists.return_value = False
            response = self.client.get("/")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("api", data)
            self.assertIn("tro.", str(data))


class TestSpaFallback(unittest.TestCase):
    """Verify SPA client-side routing fallback behavior."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_spa.db")
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        init_db(self.engine)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_spa_client_side_routes_return_200(self) -> None:
        """Client-side routes like /login, /dashboard, /verify/<token> must return 200."""
        for route in ["/login", "/dashboard", "/verify/token-xyz", "/rooms/manage"]:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Route {route} did not return 200")

    def test_spa_fallback_dev_mode_when_no_dist(self) -> None:
        """When frontend is not built, SPA fallback returns friendly JSON hint."""
        with patch("backend.app.main.DIST_INDEX") as mock_dist_index:
            mock_dist_index.exists.return_value = False
            response = self.client.get("/dashboard")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("status"), "running")
            self.assertIn("Frontend not built", data.get("message", ""))

    def test_spa_serves_static_file_in_dist(self) -> None:
        """If an exact file exists in dist/, GET /<file> should return it."""
        dist_existed = DIST_DIR.exists()
        DIST_DIR.mkdir(parents=True, exist_ok=True)
        test_file = DIST_DIR / "robots.txt"
        test_file.write_text("User-agent: *\nDisallow:", encoding="utf-8")
        try:
            response = self.client.get("/robots.txt")
            self.assertEqual(response.status_code, 200)
            self.assertIn("User-agent", response.text)
        finally:
            if test_file.exists():
                test_file.unlink()
            if not dist_existed and DIST_DIR.exists():
                try:
                    DIST_DIR.rmdir()
                except OSError:
                    pass

    def test_spa_path_traversal_prevented(self) -> None:
        """Paths trying directory traversal must return 404."""
        response = self.client.get("/../../secret.txt")
        self.assertEqual(response.status_code, 404)

    def test_spa_path_traversal_prevented_when_no_dist(self) -> None:
        """Paths trying directory traversal must return 404 even when dist is not built."""
        with patch("backend.app.main.DIST_INDEX") as mock_dist_index:
            mock_dist_index.exists.return_value = False
            response = self.client.get("/../../secret.txt")
            self.assertEqual(response.status_code, 404)


class TestStaticAssets(unittest.TestCase):
    """Verify mounted static assets serving under /assets."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_assets_serves_existing_file(self) -> None:
        """If assets directory has files, GET /assets/<file> returns 200."""
        if not ASSETS_DIR.exists():
            self.skipTest("Assets directory does not exist.")
        asset_files = [f.name for f in ASSETS_DIR.iterdir() if f.is_file()]
        if not asset_files:
            dummy_asset = ASSETS_DIR / "test_asset.js"
            dummy_asset.write_text("console.log('tro');", encoding="utf-8")
            try:
                response = self.client.get("/assets/test_asset.js")
                self.assertEqual(response.status_code, 200)
            finally:
                if dummy_asset.exists():
                    dummy_asset.unlink()
        else:
            response = self.client.get(f"/assets/{asset_files[0]}")
            self.assertEqual(response.status_code, 200)

    def test_assets_nonexistent_file_returns_404(self) -> None:
        """GET /assets/non_existent_bundle.js must return 404, not fallback to index.html."""
        response = self.client.get("/assets/non_existent_bundle.js")
        self.assertEqual(response.status_code, 404)

    def test_assets_response_has_content_type_header(self) -> None:
        """GET /assets/<file> must provide a Content-Type header."""
        if not ASSETS_DIR.exists():
            self.skipTest("Assets directory does not exist.")
        asset_files = [f.name for f in ASSETS_DIR.iterdir() if f.is_file()]
        if not asset_files:
            dummy_asset = ASSETS_DIR / "test_mime.css"
            dummy_asset.write_text("body { margin: 0; }", encoding="utf-8")
            try:
                response = self.client.get("/assets/test_mime.css")
                self.assertEqual(response.status_code, 200)
                self.assertIn("content-type", response.headers)
            finally:
                if dummy_asset.exists():
                    dummy_asset.unlink()
        else:
            response = self.client.get(f"/assets/{asset_files[0]}")
            self.assertEqual(response.status_code, 200)
            self.assertIn("content-type", response.headers)


class TestApiNotFoundReturns404(unittest.TestCase):
    """Verify that unknown API paths return 404 and are NOT swallowed by SPA catch-all."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_server_api.db")
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        init_db(self.engine)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_unknown_api_v1_route_returns_404(self) -> None:
        """GET /api/v1/non_existent_route must return 404, not 200."""
        response = self.client.get("/api/v1/non_existent_route")
        self.assertEqual(response.status_code, 404)

    def test_unknown_api_deep_path_returns_404(self) -> None:
        """GET /api/v1/deep/unknown/path must return 404."""
        response = self.client.get("/api/v1/deep/unknown/path")
        self.assertEqual(response.status_code, 404)

    def test_bare_api_returns_404(self) -> None:
        """GET /api and GET /api/ must return 404."""
        self.assertEqual(self.client.get("/api").status_code, 404)
        self.assertEqual(self.client.get("/api/").status_code, 404)

    def test_health_endpoint_still_accessible(self) -> None:
        """GET /health must remain available and return 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("app"), "tro.")


class TestSpaProtectsApiNamespace(unittest.TestCase):
    """Verify that the serve_spa catch-all endpoint correctly guards /api/ namespace."""

    def test_spa_handler_raises_404_for_api_paths(self) -> None:
        """The serve_spa function must raise HTTPException 404 for api/ sub-paths."""
        with self.assertRaises(HTTPException) as ctx:
            serve_spa("api/v1/whatever")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_spa_handler_raises_404_for_api_root(self) -> None:
        """The serve_spa function must raise HTTPException 404 for 'api/'."""
        with self.assertRaises(HTTPException) as ctx:
            serve_spa("api/")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_spa_handler_raises_404_for_bare_api(self) -> None:
        """The serve_spa function must raise HTTPException 404 for bare 'api' (no trailing slash)."""
        with self.assertRaises(HTTPException) as ctx:
            serve_spa("api")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_spa_handler_raises_404_for_health(self) -> None:
        """The serve_spa function must raise HTTPException 404 for 'health'."""
        with self.assertRaises(HTTPException) as ctx:
            serve_spa("health")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_spa_handler_raises_404_for_health_subpath(self) -> None:
        """The serve_spa function must raise HTTPException 404 for 'health/' sub-paths."""
        with self.assertRaises(HTTPException) as ctx:
            serve_spa("health/status")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_spa_handler_raises_404_for_bare_assets(self) -> None:
        """The serve_spa function must raise HTTPException 404 for bare 'assets'."""
        with self.assertRaises(HTTPException) as ctx:
            serve_spa("assets")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_spa_handler_raises_404_for_assets_subpath(self) -> None:
        """The serve_spa function must raise HTTPException 404 for 'assets/' sub-paths."""
        with self.assertRaises(HTTPException) as ctx:
            serve_spa("assets/bundle.js")
        self.assertEqual(ctx.exception.status_code, 404)


class TestRunPyArgparser(unittest.TestCase):
    """Verify the run.py argument parser produces correct defaults and flags."""

    def _get_parser(self) -> argparse.ArgumentParser:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_launcher",
            str(Path(__file__).resolve().parent.parent / "run.py"),
        )
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod._build_parser()

    def test_default_host(self) -> None:
        original = os.environ.pop("HOST", None)
        try:
            parser = self._get_parser()
            args = parser.parse_args([])
            self.assertEqual(args.host, "0.0.0.0")
        finally:
            if original is not None:
                os.environ["HOST"] = original

    def test_default_port(self) -> None:
        original = os.environ.pop("PORT", None)
        try:
            parser = self._get_parser()
            args = parser.parse_args([])
            self.assertEqual(args.port, 8000)
        finally:
            if original is not None:
                os.environ["PORT"] = original

    def test_custom_host_and_port(self) -> None:
        parser = self._get_parser()
        args = parser.parse_args(["--host", "127.0.0.1", "--port", "9000"])
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 9000)

    def test_reload_flag_default_false(self) -> None:
        parser = self._get_parser()
        args = parser.parse_args([])
        self.assertFalse(args.reload)

    def test_reload_flag_can_be_enabled(self) -> None:
        parser = self._get_parser()
        args = parser.parse_args(["--reload"])
        self.assertTrue(args.reload)

    def test_no_open_flag_default_false(self) -> None:
        parser = self._get_parser()
        args = parser.parse_args([])
        self.assertFalse(args.no_open)

    def test_no_open_flag_can_be_set(self) -> None:
        parser = self._get_parser()
        args = parser.parse_args(["--no-open"])
        self.assertTrue(args.no_open)

    def test_build_frontend_flag_default_false(self) -> None:
        parser = self._get_parser()
        args = parser.parse_args([])
        self.assertFalse(args.build_frontend)

    def test_build_frontend_flag_can_be_set(self) -> None:
        parser = self._get_parser()
        args = parser.parse_args(["--build-frontend"])
        self.assertTrue(args.build_frontend)

    def test_port_env_var_respected(self) -> None:
        original = os.environ.get("PORT")
        os.environ["PORT"] = "7777"
        try:
            parser = self._get_parser()
            args = parser.parse_args([])
            self.assertEqual(args.port, 7777)
        finally:
            if original is None:
                del os.environ["PORT"]
            else:
                os.environ["PORT"] = original

    def test_host_env_var_respected(self) -> None:
        original = os.environ.get("HOST")
        os.environ["HOST"] = "192.168.1.100"
        try:
            parser = self._get_parser()
            args = parser.parse_args([])
            self.assertEqual(args.host, "192.168.1.100")
        finally:
            if original is None:
                del os.environ["HOST"]
            else:
                os.environ["HOST"] = original

    def test_port_env_var_empty_fallback(self) -> None:
        """An empty PORT env var must safely default to 8000 without raising ValueError."""
        original = os.environ.get("PORT")
        os.environ["PORT"] = ""
        try:
            parser = self._get_parser()
            args = parser.parse_args([])
            self.assertEqual(args.port, 8000)
        finally:
            if original is None:
                del os.environ["PORT"]
            else:
                os.environ["PORT"] = original

    def test_port_env_var_invalid_string_fallback(self) -> None:
        """A non-numeric PORT env var must safely default to 8000."""
        original = os.environ.get("PORT")
        os.environ["PORT"] = "not_a_number"
        try:
            parser = self._get_parser()
            args = parser.parse_args([])
            self.assertEqual(args.port, 8000)
        finally:
            if original is None:
                del os.environ["PORT"]
            else:
                os.environ["PORT"] = original

    def test_host_env_var_empty_fallback(self) -> None:
        """An empty HOST env var must safely default to 0.0.0.0."""
        original = os.environ.get("HOST")
        os.environ["HOST"] = ""
        try:
            parser = self._get_parser()
            args = parser.parse_args([])
            self.assertEqual(args.host, "0.0.0.0")
        finally:
            if original is None:
                del os.environ["HOST"]
            else:
                os.environ["HOST"] = original


class TestRunPyExecution(unittest.TestCase):
    """Verify execution logic in run.py (launcher entry point and helpers)."""

    def _get_run_module(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_launcher_exec",
            str(Path(__file__).resolve().parent.parent / "run.py"),
        )
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    def test_check_frontend_when_already_exists(self) -> None:
        mod = self._get_run_module()
        with patch.object(Path, "exists", return_value=True):
            with patch("subprocess.run") as mock_sub:
                mod._check_frontend(build=True)
                mock_sub.assert_not_called()

    def test_check_frontend_when_missing_and_build_false(self) -> None:
        mod = self._get_run_module()
        with patch.object(Path, "exists", return_value=False):
            with patch("subprocess.run") as mock_sub:
                mod._check_frontend(build=False)
                mock_sub.assert_not_called()

    def test_check_frontend_when_missing_and_build_true(self) -> None:
        mod = self._get_run_module()
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch.object(Path, "exists", return_value=False):
            with patch("subprocess.run", return_value=mock_result) as mock_sub:
                mod._check_frontend(build=True)
                mock_sub.assert_called_once()

    def test_check_frontend_handles_filenotfound_gracefully(self) -> None:
        """If npm is not installed (FileNotFoundError), _check_frontend logs warning and returns."""
        mod = self._get_run_module()
        with patch.object(Path, "exists", return_value=False):
            with patch("subprocess.run", side_effect=FileNotFoundError("npm not found")):
                mod._check_frontend(build=True)  # Must not raise FileNotFoundError

    def test_main_invokes_init_db_and_uvicorn(self) -> None:
        mod = self._get_run_module()
        with patch("backend.app.database.init_db") as mock_init_db, \
             patch.object(mod, "_check_frontend"):
            mock_uvicorn = MagicMock()
            with patch.dict(sys.modules, {"uvicorn": mock_uvicorn}):
                mod.main(["--no-open", "--host", "127.0.0.1", "--port", "9999", "--reload"])
                mock_init_db.assert_called_once()
                mock_uvicorn.run.assert_called_once_with(
                    "backend.app.main:app",
                    host="127.0.0.1",
                    port=9999,
                    reload=True,
                )


class TestDistDirConstants(unittest.TestCase):
    """Smoke-test that DIST_DIR and DIST_INDEX are correctly resolved."""

    def test_dist_dir_points_to_frontend_dist(self) -> None:
        self.assertTrue(str(DIST_DIR).endswith(str(Path("frontend") / "dist")))

    def test_dist_index_is_inside_dist_dir(self) -> None:
        self.assertEqual(DIST_INDEX, DIST_INDEX.parent / "index.html")

    def test_dist_index_parent_matches_dist_dir(self) -> None:
        self.assertEqual(DIST_INDEX.parent, DIST_DIR)

    def test_assets_dir_points_to_dist_assets(self) -> None:
        self.assertEqual(ASSETS_DIR, DIST_DIR / "assets")


if __name__ == "__main__":
    unittest.main()
