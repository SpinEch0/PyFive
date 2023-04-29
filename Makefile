run:
	git submodule update --init --recursive
	cd xv6-riscv && make && riscv64-unknown-elf-objcopy -O binary kernel/kernel  kernel.img && make fs.img
	@export PYTHONPATH="`pwd`/pyfive:${PYTHONPATH}" && python3 pyfive/cli.py xv6-riscv/kernel.img xv6-riscv/fs.img
pytest:
	python3 -m pytest -s .
