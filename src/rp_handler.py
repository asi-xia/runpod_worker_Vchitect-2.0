import runpod
from runpod.serverless.utils import rp_upload
import shortuuid
import json
import urllib.request
import urllib.parse
import time
import os
import requests
import base64
from io import BytesIO

# Time to wait between API check attempts in milliseconds
COMFY_API_AVAILABLE_INTERVAL_MS = 250
# Maximum number of API check attempts
COMFY_API_AVAILABLE_MAX_RETRIES = 6000
# Time to wait between poll attempts in milliseconds
COMFY_POLLING_INTERVAL_MS = int(os.environ.get("COMFY_POLLING_INTERVAL_MS", 500))
# Maximum number of poll attempts
COMFY_POLLING_MAX_RETRIES = int(os.environ.get("COMFY_POLLING_MAX_RETRIES", 6000))
# Enforce a clean state after each job is done
# see https://docs.runpod.io/docs/handler-additional-controls#refresh-worker
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"


def validate_input(job_input):
    """
    Validates the input for the handler function.

    Args:
        job_input (dict): The input data to validate.

    Returns:
        tuple: A tuple containing the validated data and an error message, if any.
               The structure is (validated_data, error_message).
    """
    # Validate if job_input is provided
    if job_input is None:
        return None, "Please provide input"

    # Check if input is a string and try to parse it as JSON
    if isinstance(job_input, str):
        try:
            job_input = json.loads(job_input)
        except json.JSONDecodeError:
            return None, "Invalid JSON format in input"

    # Validate 'workflow' in input
    workflow = job_input.get("workflow")
    if workflow is None:
        return None, "Missing 'workflow' parameter"

    # Return validated data and no error
    return {"workflow": workflow}, None

def base64_encode(img_path):
    """
    Returns base64 encoded image.

    Args:
        img_path (str): The path to the image

    Returns:
        str: The base64 encoded image
    """
    with open(img_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return f"{encoded_string}"

def process_output_images(file_name):
    """
    This function takes the "outputs" from image generation and the job ID,
    then determines the correct way to return the image, either as a direct URL
    to an AWS S3 bucket or as a base64 encoded string, depending on the
    environment configuration.

    Args:
        outputs (dict): A dictionary containing the outputs from image generation,
                        typically includes node IDs and their respective output data.
        job_id (str): The unique identifier for the job.

    Returns:
        dict: A dictionary with the state ('finished' or 'failed') and the message,
              which is either the URL to the image in the AWS S3 bucket or a base64
              encoded string of the image. In case of error, the message details the issue.

    The function works as follows:
    - It first determines the output path for the images from an environment variable,
      defaulting to "/comfyui/output" if not set.
    - It then iterates through the outputs to find the filenames of the generated images.
    - After confirming the existence of the image in the output folder, it checks if the
      AWS S3 bucket is configured via the BUCKET_ENDPOINT_URL environment variable.
    - If AWS S3 is configured, it uploads the image to the bucket and returns the URL.
    - If AWS S3 is not configured, it encodes the image in base64 and returns the string.
    - If the image file does not exist in the output folder, it returns an error status
      with a message indicating the missing image file.
    """

    # The path where ComfyUI stores the generated images
    VchitectXL_OUTPUT_PATH = os.environ.get("VchitectXL_OUTPUT_PATH", "/Vchitect-2.0/output")
    job_id = shortuuid.uuid()
    output_images = file_name

    print(f"runpod-worker-VchitectXL - video generation is done")

    # expected image output folder
    local_image_path = f"{VchitectXL_OUTPUT_PATH}/{output_images}"

    print(f"runpod-worker-VchitectXL - {local_image_path}")

    # The image is in the output folder
    if os.path.exists(local_image_path):
        if os.environ.get("BUCKET_ENDPOINT_URL", False):
            # URL to image in AWS S3
            image = rp_upload.upload_image(job_id, local_image_path)
            print(
                "runpod-worker-VchitectXL - the file was generated and uploaded to AWS S3"
            )
        else:
            # base64 image
            image = base64_encode(local_image_path)
            print(
                "runpod-worker-VchitectXL - the file was generated and converted to base64"
            )

        return {
            "state": "finished",
            "file_url": image,
            "message": "task is completed - the file was generated and uploaded to AWS S3",
        }
    else:
        print("runpod-worker-VchitectXL - the file does not exist in the output folder")
        return {
            "state": "failed",
            "message": f"the file does not exist in the specified output folder: {local_image_path}",
        }


def handler(job):
    """
    The main function that handles a job of generating an image.

    This function validates the input, sends a prompt to ComfyUI for processing,
    polls ComfyUI for result, and retrieves generated images.

    Args:
        job (dict): A dictionary containing job details and input parameters.

    Returns:
        dict: A dictionary containing either an error message or a success status with generated images.
    """
    job_input = job["input"]

    # Make sure that the input is valid
    validated_data, error_message = validate_input(job_input)
    if error_message:
        return {"state": "failed", 'message': 'task execution failed', "error": error_message}

    # Extract validated data
    workflow = validated_data["workflow"]
    print(f"runpod-worker-VchitectXL - wait until video generation is complete")
    # run the inference
    try:
        print(f"runpod-worker-VchitectXL - queued workflow")
    except Exception as e:
        return {"state": "failed", 'message': 'task execution failed', "error": f"Error queuing workflow: {str(e)}"}
    
    # Get the generated image and return it as URL in an AWS bucket or as base64
    file_name = 'zhihui_001.mp4'
    images_result = process_output_images(file_name)

    result = {**images_result, "refresh_worker": REFRESH_WORKER}

    return result


# Start the handler only if this script is run directly
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
