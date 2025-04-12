from collections.abc import Generator
from typing import Any
from PIL import Image
import io

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.file.file import File


class ImageCompressionTool(Tool):

    def compress_image(self,image_file: bytes, quality: int = 85) -> bytes:
        """
        压缩图片文件

        :param image_file: 图片文件的字节流
        :param quality: 压缩质量（1-100），默认 85
        :return: 压缩后的图片字节流
        """
        try:
            # 打开图片
            with Image.open(io.BytesIO(image_file)) as img:
                print("图片压缩开始")

                # 转换为 RGB 模式（如果不是）
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # 创建字节流缓冲区
                output = io.BytesIO()

                # 保存压缩后的图片到缓冲区
                img.save(output, format=img.format, quality=quality)
                output.seek(0)

                return output.read()
        except Exception as e:
            raise ValueError(f"图片压缩失败: {e}")

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        imgs = tool_parameters.get("input_image")
        host_url = tool_parameters.get("host_url")
        target_size = tool_parameters.get("target_size")
        if not imgs:
            yield self.create_json_message(
                {
                    "result": "请提供图片文件"
                }
            )
            return
        if not isinstance(imgs, list):
            yield self.create_json_message({
                "result": "请提供图片文件列表"
            })
            return
        for img in imgs:
            # 获取正确的字节流数据
            if isinstance(img, File):
                try:
                    # 先判断File mime 是否为图片类型
                    if img.mime_type not in ["image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"]:
                        yield self.create_json_message({
                            "result": f"不支持的文件类型: {img.mime_type}"
                        })
                        continue
                    url = img.url
                    if not url.startswith(('http://', 'https://')):
                        # 去掉末尾的斜杠
                        host_url = host_url.rstrip('/')
                        url = f"{host_url}/{url}"
                    import requests
                    response = requests.get(url)
                    response.raise_for_status()
                    input_image_bytes = response.content
                    # input_image_bytes = img.blob
                except Exception as e:
                    yield self.create_json_message({
                        "result": f"下载图片失败: {str(e)}"
                    })
                    continue
            elif isinstance(img, bytes):
                input_image_bytes = img
            else:
                yield self.create_json_message({
                    "result": f"不支持的图片类型: {type(img)}"
                })
                continue

            # MB to B
            t_c_size = target_size * 1024 * 1024
            # 计算压缩质量
            if target_size > 0:
                # 计算压缩质量
                quality = int(100 * t_c_size / len(input_image_bytes))
                # 限制压缩质量范围
                if quality < 1:
                    quality = 1
                elif quality > 100:
                    quality = 100
            else:
                quality = 85

            # 压缩图片
            compressed_img = self.compress_image(input_image_bytes, quality=quality)

            meta = {
                "filename": img.filename if isinstance(img, File) else "compressed_image.jpg",
                "mime_type": img.mime_type,
                "size": len(compressed_img),
            }
            yield self.create_blob_message(compressed_img, meta)



