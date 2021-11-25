import json
import os
import os.path as osp
import posixpath
import constants
import subprocess


class Pipeline:
    def __init__(self):
        self.path = posixpath.join(os.getcwd())
        self.output = None

    def convert_model(self, input_json=None, convert_directory=None):
        with open(posixpath.join(self.path, input_json), 'r') as f:
            json_data = json.load(f)
        convert_cmd = "olive convert "
        for p in ["model_path", "model_root_path", "input_names", "output_names", "input_shapes", "output_shapes", "input_types", "output_types", "model_framework", "onnx_opset",
                  "sample_input_data_path", "framework_version", "conversion_config"]:
            if json_data.get(p):
                convert_cmd = convert_cmd + " --{} {}".format(p, json_data[p])

        onnx_model_path = os.path.join(convert_directory, json_data['onnx_model_path'])
        cvt_config_json = json_data.get("conversion_config")
        if cvt_config_json:
            with open(cvt_config_json, 'r') as f:
                cvt_config_data = json.load(f)
            cvt_config_data["onnx_model_path"] = onnx_model_path
            with open(cvt_config_json, 'w') as f:
                json.dump(cvt_config_data, f)
        else:
            convert_cmd = convert_cmd + " --onnx_model_path {}".format(onnx_model_path)
        p = subprocess.run(convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
        self.output = str(p.stderr.decode("utf-8"))

        return onnx_model_path

    def perf_tuning(self, result_dir=None, input_json=None):
        with open(posixpath.join(self.path, input_json), 'r') as f:
            json_data = json.load(f)
        perf_tuning_cmd = "olive optimize "
        for p in ["model_path", "concurrency_num", "test_num", "warmup_num", "omp_max_active_levels",
                  "input_names", "output_names", "input_shapes", "sample_input_data_path", "intra_thread_num_list", "inter_thread_num_list",
                  "providers_list", "execution_mode_list", "ort_opt_level_list", "optimization_config",
                  "transformer_args", "omp_wait_policy_list", "onnxruntime_version", "max_latency_percentile", "max_latency_sec", "dynamic_batching_size", "threads_num", "min_duration_sec"]:
            if json_data.get(p):
                perf_tuning_cmd = perf_tuning_cmd + " --{} {}".format(p, json_data[p])
        for p in ["use_gpu", "trt_fp16_enabled", "quantization_enabled", "transformer_enabled", "throughput_tuning_enabled"]:
            if json_data.get(p):
                perf_tuning_cmd = perf_tuning_cmd + " --{}".format(p)

        opt_config_json = json_data.get("optimization_config")
        if opt_config_json:
            with open(opt_config_json, 'r') as f:
                opt_config_data = json.load(f)
            opt_config_data["result_path"] = result_dir

            with open(opt_config_json, 'w') as f:
                json.dump(opt_config_data, f)
        else:
            perf_tuning_cmd = perf_tuning_cmd + " --result_path {}".format(result_dir)

        p = subprocess.run(perf_tuning_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=True)
        self.output = str(p.stderr.decode("utf-8"))
        optimized_model_path = os.path.join(result_dir, "optimized_model.onnx")
        return result_dir, optimized_model_path

    def get_result(self, result=None, optimized_model_path=None):
        return Pipeline.Result(result, optimized_model_path)

    def win_path_to_linux_relative(self, path):
        return osp.relpath(path).replace("\\", "/")

    class Result:
        def __init__(self, result_directory, optimized_model_path):
            """Construct by the result directory generated by perf_test"""
            perf_result_json = osp.join(result_directory, constants.PERF_RESULT_JSON)
            if osp.exists(perf_result_json):
                with open(perf_result_json) as json_file:
                    olive_result = json.load(json_file)
                    results = olive_result.get("all_tuning_results")
                    best_test_name = olive_result.get("best_test_name")
                    pretuning_test_name = "pretuning"
                    for result in results:
                        if result.get("test_name") == best_test_name:
                            self.execution_provider = result.get("execution_provider", "Not Required")
                            self.env_vars = result.get("env_vars", "Not Required")
                            self.session_options = result.get("session_options", "Not Required")
                            self.latency_ms_avg = result.get("latency_ms").get("avg")
                            self.latency_ms_p90 = result.get("latency_ms").get("latency_p90")
                            self.latency_ms_p95 = result.get("latency_ms").get("latency_p95")
                            self.optimal_throughput = result.get("throughput")
                        if result.get("test_name") == pretuning_test_name:
                            self.pretuning_avg = result.get("latency_ms").get("avg")
                            self.pretuning_throughput = result.get("throughput")
                    self.optimized_model = optimized_model_path
                    self.sample_script = self.__generate_sample_script()
            else:
                raise RuntimeError('Cannot find result directory.')

        def __generate_sample_script(self):
            model_path = self.optimized_model
            sample_script_line = ["import onnxruntime as ort", "model_path = {}".format(model_path),
                                  "sess_options = ort.SessionOptions()"]
            if self.session_options != "Not Required":
                session_opt_lines = ["sess_options.{} = {}".format(key, value) for key, value in
                                     self.session_options.items()]
                sample_script_line.extend(session_opt_lines)
            if self.env_vars != "Not Required":
                env_lines = ["os.environ[\'{}\'] = \'{}\'".format(key, value) for key, value in self.env_vars.items()]
                sample_script_line.extend(env_lines)
            if self.execution_provider:
                session_creation = [
                    "onnx_session = ort.InferenceSession(model_path, sess_options, providers=[{}])".format(
                        self.execution_provider)]
            else:
                session_creation = ["onnx_session = ort.InferenceSession(model_path, sess_options)"]
            sample_script_line.extend(session_creation)

            return sample_script_line

