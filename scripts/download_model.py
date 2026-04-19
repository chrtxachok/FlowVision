from transformers import DonutProcessor, VisionEncoderDecoderModel

model_name = "naver-clova-ix/donut-base"
processor = DonutProcessor.from_pretrained(model_name)
model = VisionEncoderDecoderModel.from_pretrained(model_name)

# Сохраняем локально, чтобы больше не зависеть от сети
processor.save_pretrained("./models/donut-base")
model.save_pretrained("./models/donut-base")
print("Модель успешно скачана в папку ./models/donut-base")