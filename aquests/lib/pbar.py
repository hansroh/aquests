import tqdm

def get_pbar (total, desc = "Progress"):
	return tqdm.tqdm (desc = desc, total = total)
