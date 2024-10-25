import unittest
from unittest.mock import patch
from packaging.version import Version
from envmanager import (
    EnvManager,
    create_virtual_env,
    get_or_create_virtual_env,
    get_virtual_env,
)
import tempfile
import shutil
import os


class TestGetOrCreateVirtualEnv(unittest.TestCase):
    def setUp(self):
        self.temppath = tempfile.mkdtemp()
        self.env_path = os.path.join(self.temppath, "test_env")

    def tearDown(self):
        shutil.rmtree(self.temppath)

    def test_get_unexisting_virtual_env(self):
        # Test creating a new virtual environment
        with self.assertRaises(ValueError):
            get_virtual_env(self.env_path)

    def test_create_virtual_env(self):
        # Test creating a new virtual environment
        env_manager = create_virtual_env(self.env_path)
        self.assertIsInstance(env_manager, EnvManager)
        self.assertIsInstance(get_virtual_env(self.env_path), EnvManager)

    def test_get_or_create_virtual_env_existing(self):
        # Test returning an existing virtual environment
        env_manager, created = get_or_create_virtual_env(self.env_path)
        self.assertTrue(created)
        self.assertIsInstance(env_manager, EnvManager)
        env_manager, created = get_or_create_virtual_env(self.env_path)
        self.assertFalse(created)
        self.assertIsInstance(env_manager, EnvManager)


class TestEnvManager(unittest.TestCase):
    #
    @classmethod
    def setUpClass(cls):
        cls.temppath = tempfile.mkdtemp()
        cls.env_path = os.path.join(cls.temppath, "test_env")
        cls.env_manager, _ = get_or_create_virtual_env(cls.env_path)
        cls.testpackage_name = "dummy_test"
        cls.testpackage_version = "0.1.2"
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temppath)

    @patch("envmanager.os.path.isfile")
    @patch("envmanager.platform.system")
    def test_get_python_executable_windows(self, mock_platform, mock_isfile):
        # Test for Windows environment
        mock_platform.return_value = "Windows"
        mock_isfile.return_value = True
        self.assertEqual(
            self.env_manager.get_python_executable(),
            os.path.join(self.env_path, "Scripts", "python.exe"),
        )

    @patch("envmanager.os.path.isfile")
    @patch("envmanager.platform.system")
    def test_get_python_executable_unix(self, mock_platform, mock_isfile):
        # Test for Unix-based environment
        mock_platform.return_value = "Linux"
        mock_isfile.return_value = True
        self.assertEqual(
            self.env_manager.get_python_executable(),
            os.path.join(self.env_path, "bin", "python"),
        )

    def test_install_package(self):
        # Test successful package installation
        self.env_manager.install_package(
            self.testpackage_name, version=self.testpackage_version
        )
        self.assertTrue(self.env_manager.package_is_installed(self.testpackage_name))

    def test_install_package_failure(self):
        # Test failed package installation
        with self.assertRaises(ValueError):
            self.env_manager.install_package("nonexistent_package" + (str(os.getpid())))

    def _assert_package_installed(self):
        if not self.env_manager.package_is_installed(self.testpackage_name):
            self.env_manager.install_package(
                self.testpackage_name, version=self.testpackage_version
            )

    def test_check_version(self):
        # Test package version check
        self._assert_package_installed()
        self.assertTrue(self.env_manager.package_is_installed(self.testpackage_name))
        version = self.env_manager.get_package_version(self.testpackage_name)
        self.assertIsInstance(version, Version)
        self.assertEqual(version, Version(self.testpackage_version))

    def test_all_packages(self):
        # Test listing all installed packages
        self._assert_package_installed()
        packages = self.env_manager.all_packages()
        self.assertIsInstance(packages, list)
        self.assertTrue(len(packages) > 0)
        names = [package["name"] for package in packages]
        self.assertIn(self.testpackage_name, names)

    def test_local_package(self):
        # Test getting a local package
        self._assert_package_installed()
        package = self.env_manager.get_local_package(self.testpackage_name)
        self.assertIsNotNone(package)
        self.assertEqual(package["name"], self.testpackage_name)
        self.assertEqual(package["version"], Version(self.testpackage_version))

    def test_package_version(self):
        # Test getting the package version
        self._assert_package_installed()
        version = self.env_manager.get_package_version(self.testpackage_name)
        self.assertEqual(version, Version(self.testpackage_version))

    def test_package_info(self):
        # Test getting package information
        package_data = self.env_manager.get_remote_package(self.testpackage_name)
        self.assertIsNotNone(package_data)
        self.assertIn("info", package_data)
        self.assertIn("name", package_data["info"])
        self.assertEqual(package_data["info"]["name"], self.testpackage_name)
        self.assertIn("version", package_data["info"])
        self.assertGreater(
            Version(package_data["info"]["version"]), Version(self.testpackage_version)
        )

    def test_package_update_available(self):
        # Test package update availability
        self._assert_package_installed()
        (
            update_available,
            latest_version,
            current_version,
        ) = self.env_manager.package_update_available(self.testpackage_name)
        self.assertTrue(update_available)
        self.assertGreater(latest_version, current_version)

    def test_update_package(self):
        # Test package update
        self._assert_package_installed()
        self.assertTrue(self.env_manager.package_is_installed(self.testpackage_name))
        self.env_manager.install_package(self.testpackage_name, upgrade=True)
        self.assertTrue(self.env_manager.package_is_installed(self.testpackage_name))
        self.assertGreater(
            self.env_manager.get_package_version(self.testpackage_name),
            Version(self.testpackage_version),
        )

    def test_run_module(self):
        # Test running a module
        self._assert_package_installed()
        self.env_manager.run_module("pip", ["--version"])

    def test_uninstall_package(self):
        # Test uninstalling a package
        self._assert_package_installed()
        self.assertTrue(self.env_manager.package_is_installed(self.testpackage_name))
        self.env_manager.remove_package(self.testpackage_name)
        self.assertFalse(self.env_manager.package_is_installed(self.testpackage_name))
