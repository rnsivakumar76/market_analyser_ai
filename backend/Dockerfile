FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies if any
RUN yum install -y ca-certificates

# Install Python requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy logic to Lambda Task Root
COPY . ${LAMBDA_TASK_ROOT}

# Start the Mangum APIGW Handler
CMD ["app.main.handler"]
