"""pytest 全局：在导入任何 app 模块之前锁定隔离的数据目录（config 在 import 时读环境变量）。"""
import os
import tempfile

os.environ.setdefault("SHANJIAN_DATA_DIR", tempfile.mkdtemp(prefix="shanjian_test_"))
