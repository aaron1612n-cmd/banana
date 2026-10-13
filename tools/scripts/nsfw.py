"""Zero-shot CLIP banana scoring. usage: classify.py OUT.json ROOT LISTFILE  (LISTFILE: one path per line, relative to ROOT)"""
import json, os, sys, torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

OUT, ROOT, LIST = sys.argv[1:4]
POS = ["a woman in a bikini", "a swimsuit model posing", "a person in lingerie or underwear", "a shirtless man", "a nude person",
       "a sexually suggestive photo", "cleavage", "a woman in a revealing outfit", "a beauty pageant contestant in a swimsuit", "a burlesque dancer"]
NEG = ["a photo of bananas", "a banana plant", "food on a plate", "a dessert", "a person in a banana costume", "a fully clothed person",
       "a child eating a banana", "a group of people", "a market", "a landscape", "a drawing", "a product package", "an animal", "a building"]
def feat(o):
    return o if torch.is_tensor(o) else o.pooler_output

torch.set_num_threads(os.cpu_count())
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch16").eval()
proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch16")
with torch.no_grad():
    t = proc(text=POS + NEG, return_tensors="pt", padding=True)
    tf = feat(model.get_text_features(**t)); tf = tf / tf.norm(dim=-1, keepdim=True)
labels = POS + NEG
paths = [l.strip() for l in open(LIST) if l.strip()]
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
todo = [p for p in paths if p not in res]
B = 32
for i in range(0, len(todo), B):
    batch, ims = [], []
    for p in todo[i:i + B]:
        try:
            im = Image.open(os.path.join(ROOT, p)).convert("RGB"); im.thumbnail((448, 448)); ims.append(im); batch.append(p)
        except Exception as e:
            res[p] = {"score": -1, "top": f"error {e}"}
    if not ims:
        continue
    with torch.no_grad():
        f = feat(model.get_image_features(**proc(images=ims, return_tensors="pt"))); f = f / f.norm(dim=-1, keepdim=True)
        probs = (100 * f @ tf.T).softmax(dim=-1)
    for p, pr in zip(batch, probs):
        res[p] = {"score": round(float(pr[:len(POS)].sum()), 4), "top": labels[int(pr.argmax())]}
    if (i // B) % 20 == 0:
        json.dump(res, open(OUT, "w")); print(len(res), "scored", flush=True)
json.dump(res, open(OUT, "w")); print("done", len(res), flush=True)
