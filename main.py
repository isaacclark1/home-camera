from picamera2 import Picamera2
import io
from threading import Condition
from picamera2.encoders import MJPEGEncoder, Quality
from picamera2.outputs import FileOutput
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
import logging
import libcamera

# StreamingOutput manages video frames in memory and handles safe, thread-based access
class StreamingOutput(io.BufferedIOBase):
  def __init__(self):
    super().__init__()
    self.frame = None # Holds the most recent frame from the camera
    self.condition = Condition() # Ensures safe, synchronised access to the frame
    
  # Store a new frame.
  def write(self, frame):
    with self.condition:
      self.frame = frame # Store incoming frame
      self.condition.notify_all() # Notify readers that a new frame is available
        
  # Asynchronously read the latest frame
  async def read(self):
    with self.condition:
      self.condition.wait() # Wait until a new frame is written
      return self.frame
      
# JpegStream manages the camera and the video streaming logic
class JpegStream:
  def __init__(self):
    self.active = False # Indicates if the stream is currently active
    self.connections = set() # Keeps track of active WebSocket connections
    self.picam2 = None # Stores Picamera2 instance
    self.task = None # Asynchronous task for streaming video frames
    
  # Stream video frames to connected clients
  async def stream_jpeg(self):
    self.picam2 = Picamera2()
    
    video_config = self.picam2.create_video_configuration(
      main={"size": (2560, 1440)}, # Congigure video resolution
      transform=libcamera.Transform(rotation=180) # Rotate the camera 180 degrees - modify as necessary depending on how the camera is mounted
    )
    
    self.picam2.configure(video_config) # Apply camera configuration
    
    output = StreamingOutput() # Create an output buffer for storing frames
    self.picam2.start_recording(MJPEGEncoder(), FileOutput(output), Quality.MEDIUM)
    
    try:
      # Continuously stream frames while the stream is active
      while self.active:
        jpeg_data = await output.read() # Retrieve latest frame
        
        # Send the frames to all connected WebSocket clients
        tasks = [websocket.send_bytes(jpeg_data) for websocket in self.connections.copy()]
        
        await asyncio.gather(*tasks, return_exceptions=True) # Send frames in parallel
    finally:
      # Clean up resources when streaming stops
      self.picam2.stop_recording()
      self.picam2.close()
      self.picam2 = None
  
  # Start the video stream
  async def start(self):
    if not self.active: # Only start if not active
      self.active = True
      self.task = asyncio.create_task(self.stream_jpeg())
      
  # Stop the video stream
  async def stop(self):
    if self.active:
      self.active = False # Mark the stream is inactive
      if self.task:
        await self.task # Wait for the streaming task to finish
        self.task = None
        
  # Get the active web socket connections
  def get_connections(self):
    return self.connections
        
  # Add a new WebSocket connection to the active list
  def add_connection(self, websocket):
    self.connections.add(websocket)
    
  # Remove a WebSocket connection from the active list
  def remove_connection(self, websocket):
    self.connections.remove(websocket)
        
# Create a global instance of JpegStream for managing the camera and streams
jpeg_stream = JpegStream()

# Define the application lifespan to ensure resources are cleaned up when the app stops
@asynccontextmanager
async def lifespan(app: FastAPI):
  yield # Let the app run
  await jpeg_stream.stop() # Stop the stream when the app shuts down
  
# Create the FastAPI application and set its lifespan handler
app = FastAPI(lifespan=lifespan)

# WebSocket endpoint for clients to connect and receive video streams
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
  await websocket.accept() # Accept the WebSocket connection
  jpeg_stream.add_connection(websocket) # Add the connection to the active list
  
  try:
    # Keep the connection open and handle incoming messages (even if no data is processed)
    while True:
      await websocket.receive_text() # Keep the connection alive
  except Exception as e:
    logging.error(f"WebSocket error: {e}")
  finally:
    # Remove the client from the connections list on disconnect
    jpeg_stream.remove_connection(websocket)
    # Stop the stream if there are no more clients
    if not jpeg_stream.get_connections():
      await jpeg_stream.stop()
      
# HTTP endpoint to start the video stream manually
@app.post("/start")
async def start_stream():
  await jpeg_stream.start()
  return {"message": "Stream started"}

# HTTP endpoint to stop the video stream manually
@app.post("/stop")
async def stop_stream():
  await jpeg_stream.stop()
  return {"message": "Stream stopped"}