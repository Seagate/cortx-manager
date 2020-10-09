from csm.common.process import SimpleProcess

class StorageInfo:

    @staticmethod
    def get_dir_usage(dir="", unit="K"):
        cmd = f"sudo du -B{unit} {dir}"
        return execute_cmd(cmd)

    @staticmethod
    def get_fs_usage(fs="", unit="K"):
        cmd = f"df -B{unit} {fs}"
        return execute_cmd(cmd)

    @staticmethod
    def execute_cmd(cmd=""):
        sp_es = SimpleProcess(cmd)
        Log.debug(f"Running {cmd}")
        res = sp_es.run()
        Log.debug(f"Resulted: {res}")
        return res
