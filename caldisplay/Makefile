.PHONY: device server docker docker_push

device:
	esphome run caldisplay.yaml

server:
	cd server && flask --app server --debug run

docker:
	cd server && docker build -t caldisplay .

deploy:
# ifndef TAG
# 	$(eval TAG := $(shell date "+%Y%m%d-%H%M"))
# endif
# 	docker tag caldisplay gcr.io/aeracode-207401/caldisplay:$(TAG)
# 	docker push gcr.io/aeracode-207401/caldisplay:$(TAG)
# 	gcloud run deploy caldisplay --region=us-central1 --image=gcr.io/aeracode-207401/caldisplay:$(TAG)
	docker save caldisplay | gzip | pv | ssh root@venusaur.internal.aeracode.org -- /usr/local/bin/docker load
