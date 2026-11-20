# Assignment 4: Loan EMI Calculator on Kubernetes (Minikube)

Flask app + MongoDB replica set, deployed on Minikube with Ingress and HPA.

## Structure
- app/      Flask application, Dockerfile, templates
- k8s/      Kubernetes manifests
- scripts/  Load-test and profiling scripts
- results/  Raw load-test outputs and graphs

## Run locally
    docker run -d --name mongo-test -p 27017:27017 mongo:7.0
    cd app && python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    MONGO_URL=mongodb://localhost:27017/emidb python app.py

## Deploy on Minikube
(to be completed after Milestone 2: kubectl apply -f k8s/)
