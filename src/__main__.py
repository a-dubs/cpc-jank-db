from src import aws, io

try:
    for cloud in [aws, io]:
        cloud.generate()
except AttributeError as e:
    print(f"template interface incomplete for {e}")

