DOCKER_HUB_USERNAME

DOCKER_HUB_ACCESS_TOKEN





kubectl get namespace ashapp -o json > ashapp-latest.json

nano ashapp-latest.json

make like this: -
"spec": {
  "finalizers": []
}

kubectl replace --raw "/api/v1/namespaces/ashapp/finalize" -f ./ashapp-latest.json

kubectl get ns

rm ashapp-latest.json

cd backend

docker build -t ashwanth01/flask-app:latest .

docker push ashwanth01/flask-app:latest


docker build -t ashwanth01/deployer-app:latest -f deployer-dockerfile .

docker push ashwanth01/deployer-app:latest


cd history-services

docker build -t ashwanth01/history-service:latest .

docker push ashwanth01/history-service:latest


cd ../database

docker build -t ashwanth01/flask-monitor:latest .

docker push ashwanth01/flask-monitor:latest


cd ../history-service

docker build -t ashwanth01/history-service:latest .

docker push ashwanth01/history-service:latest



docker build -t ashwanth01/ashapp-backend:latest .

docker run -d --name ashapp-backend \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(which docker):/usr/bin/docker \
  -v $(which kubectl):/usr/bin/kubectl \
  -v $HOME/.kube:/home/appuser/.kube \
  -e KUBECONFIG=/home/appuser/.kube/config \
  --user root \
  ashwanth01/ashapp-backend:latest






docker buildx build --platform linux/amd64 -t ashwanth01/history-service:latest .







