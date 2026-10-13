"""Zero-shot CLIP banana scoring. usage: classify.py OUT.json ROOT LISTFILE  (LISTFILE: one path per line, relative to ROOT)"""
import json, os, sys, torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

OUT, ROOT, LIST = sys.argv[1:4]
POS = ["a photo of bananas", "a photo of a single banana", "a bunch of bananas", "a banana plant", "a banana tree with fruit",
       "large banana leaves", "a purple banana flower", "a banana plantation", "green plantains", "fried plantain slices",
       "a loaf of banana bread", "a dessert topped with sliced bananas", "a banana split sundae", "a banana smoothie",
       "pancakes with sliced bananas", "a person wearing a banana costume", "a banana toy or banana shaped object",
       "a drawing or painting of bananas", "banana flavored snack packaging", "a banana peel", "a market stall selling bananas",
       "food served on a banana leaf", "a peeled banana", "ripe bananas with brown spots", "banana chips", "a banana pseudostem trunk"]
NEG = ["a photo of a person", "a portrait of a woman", "a portrait of a man", "a baby", "a group of people", "a crowd at a concert",
       "a building", "a city street", "a landscape", "a beach at sunset", "a car or truck", "a bicycle", "a document with text",
       "a microscope image of cells", "a bird", "a cat", "a dog", "an insect", "a plate of food", "a cake", "a cup of coffee",
       "a flower", "a forest", "a logo", "a map", "a poster", "a screenshot", "a meeting or conference", "a monkey", "a pig"]
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
