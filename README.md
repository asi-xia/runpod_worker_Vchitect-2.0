# runpod_worker_Vchitect-2.0

buid docker image的时候需要设置一下：

在该项目根目录新建文件hf_token，内容是你的Hugging Face User Access Tokens，如果您还未创建，可以参考这里 https://huggingface.co/settings/tokens
粘贴tokens后保存文件。

在命令行中运行以下命令：
Linux:
export DOCKER_BUILDKIT=1
Windows:
set DOCKER_BUILDKIT=1

之后运行
docker build --progress=plain -t 你的用户名/镜像名:镜像tag --no-cache --secret --secret id=hf_token --platform linux/amd64 .