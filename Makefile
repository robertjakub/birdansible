build:
	@ansible-playbook playbooks/build.yml -i inventory.txt

build-rs1:
	@ansible-playbook playbooks/build.yml -i inventory.txt --limit "rs1,rs1v6"

build-rs2:
	@ansible-playbook playbooks/build.yml -i inventory.txt --limit "rs2,rs2v6"

check:
	@ansible-playbook playbooks/check.yml -i inventory.txt

cache: remove irrcache makecache
updatecache: remove makecache

remove:
	@rm -f temp/cache.yml
	@touch temp/cache.yml
	@touch peers/addon.yml

makecache:
	@ansible-playbook playbooks/updatecache.yml -i inventory.txt

irrcache:
	@ansible-playbook playbooks/getirr.yml -i inventory.txt

deploy:
	@ansible-playbook playbooks/deploy.yml -i inventory.txt

deploy-retry:
	@ansible-playbook playbooks/deploy.yml -i inventory.txt --limit @deploy.retry

deploy-rs1:
	@ansible-playbook playbooks/deploy.yml -i inventory.txt --limit "rs1,rs1v6"

deploy-rs2:
	@ansible-playbook playbooks/deploy.yml -i inventory.txt --limit "rs2,rs2v6"

clean:
	@rm -f playbooks/*.retry
