# Assignment 4: Loan EMI Calculator on Kubernetes (Minikube)

Flask + MongoDB (3-member replica set) loan EMI calculator, deployed on Minikube
with NGINX Ingress, load tested with httperf and autoscaled with an HPA.

## Structure
- app/      Flask application, Dockerfile, templates
- k8s/      Kubernetes manifests (apply in file order)
- scripts/  Load-test, monitoring, HPA test and graph scripts
- results/  Raw outputs, summary.csv, evidence and graphs

## Run locally
    docker run -d --name mongo-test -p 27017:27017 mongo:7.0
    cd app && python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    MONGO_URL=mongodb://localhost:27017/emidb python app.py
Open http://localhost:8080

## Deploy on Minikube
    minikube start
    minikube addons enable ingress
    minikube addons enable metrics-server
    cd app && docker build -t emi-web:1.0 . && cd ..
    minikube image load emi-web:1.0
    kubectl apply -f k8s/
    kubectl get pods -n emi        # wait for mongo-0/1/2 and emi-web pods: 1/1 Running

## Access the app
Directly through the Service:

    kubectl port-forward svc/emi-web 8080:80 -n emi      # http://localhost:8080

Through the Ingress (host emi.local):

    # add "127.0.0.1 emi.local" to the hosts file
    kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8082:80
    # open http://emi.local:8082

## Tests and results
- scripts/spread.sh      load distribution across replicas
- scripts/loadtest.py    httperf runs at 10/25/50/100/200 req/s with 1, 2, 3 replicas
- scripts/hpa_test.py    10-minute autoscaling test
- scripts/make_graphs.py builds the three graphs in results/graphs/
- results/summary.csv    results of the 15 load-test runs
