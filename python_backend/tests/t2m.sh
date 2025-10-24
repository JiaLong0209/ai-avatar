# Test the endpoint
http -f POST http://localhost:8000/t2m text="a person is walking"

http -f POST http://localhost:8000/t2m text="a person is jumping"

curl -X POST "http://localhost:8000/t2m" \
  -F "text=a girl waves her hand happily" \
  -F "format=fbx" \
  --output motion.fbx