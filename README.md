# Project Working Screenshots

Here are some working screenshots of the project:

## Screenshots

### Screenshot 1
![Screenshot 1](working-ss/1.png)

### Screenshot 2
![Screenshot 2](working-ss/2.png)

### Screenshot 3
![Screenshot 3](working-ss/3.png)

### Screenshot 4
![Screenshot 4](working-ss/4.png)

### Screenshot 5
![Screenshot 5](working-ss/5.png)

### Screenshot 6
![Screenshot 6](working-ss/6.png)

### Screenshot 7
![Screenshot 7](working-ss/7.png)

### Screenshot 8
![Screenshot 8](working-ss/8.png)



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







