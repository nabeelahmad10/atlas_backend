FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY channel-service/requirements.txt ./channel-service/
RUN pip install --no-cache-dir -r channel-service/requirements.txt

# Copy source code
COPY backend/ ./backend/
COPY channel-service/ ./channel-service/
COPY start.sh ./

RUN chmod +x start.sh

EXPOSE 8000 8001

CMD ["./start.sh"]
