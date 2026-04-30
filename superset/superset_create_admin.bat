docker exec -it datalake-pet-superset-1 superset fab create-admin ^
  --username admin ^
  --firstname Admin ^
  --lastname User ^
  --email admin@example.com ^
  --password admin

docker exec -it datalake-pet-superset-1 superset db upgrade
docker exec -it datalake-pet-superset-1 superset init
