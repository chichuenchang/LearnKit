"""Render an image MCQ quiz to a self-contained HTML page.

Usage: python image_quiz.py --out <html_path>   (reads a quiz-spec JSON on stdin)
Output: JSON to stdout (ASCII-safe). The HTML embeds images as base64 data-URIs
and uses inline CSS/JS only (fully offline, single file).

Each question: { image_path?, stem, options[], answer_index,
                 crop_bbox?, target_bbox? }  (bboxes normalized [x,y,w,h]).
  - image_path (optional): omit for a text-only MCQ card (mixed quizzes interleave
    text and image questions). A named-but-missing image is skipped.
  - crop_bbox  (optional): crop the displayed image to this region first. Use for
    figure-bearing pool problems where the figure is part of the question.
  - target_bbox (optional): blank + highlight this region with a "?". Use for
    image-bank "name the highlighted structure" questions. Omit → no mask.
If both are given, target_bbox is interpreted relative to the cropped image
(callers normally use one or the other).
"""
import argparse
import html as htmllib
import json
import os
import sys

from imgutil import crop_norm, data_uri

CARD_TMPL = """  <section class="card" data-i="{i}">
    <div class="meta">Q {n} / {total}</div>
    <img alt="question image" src="{uri}">
    <p class="stem">{stem}</p>
    <div class="opts">
{buttons}
    </div>
    <div class="fb"></div>
  </section>"""

# Same card with no image — used for text-only MCQs in a mixed quiz.
CARD_TMPL_NOIMG = """  <section class="card" data-i="{i}">
    <div class="meta">Q {n} / {total}</div>
    <p class="stem">{stem}</p>
    <div class="opts">
{buttons}
    </div>
    <div class="fb"></div>
  </section>"""

BTN_TMPL = '      <button class="opt"{correct}>{letter}. {text}</button>'

# PAGE_TMPL is NOT str.format-ed (CSS/JS braces stay literal). Only the two
# __TITLE__ / __CARDS__ sentinels are replaced.
PAGE_TMPL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
 body{font-family:system-ui,Arial,sans-serif;max-width:820px;margin:24px auto;padding:0 14px;color:#1b1b1b}
 h1{font-size:18px}
 .bar{position:sticky;top:0;background:#fff;padding:8px 0;border-bottom:1px solid #ddd;font-weight:600}
 .card{display:none;margin:18px 0}
 .card.active{display:block}
 .card img{max-width:100%;border:1px solid #ccc;border-radius:6px}
 .meta{color:#777;font-size:13px;margin:6px 0}
 .stem{font-weight:600;margin:10px 0}
 .opts{display:flex;flex-direction:column;gap:8px}
 .opt{text-align:left;padding:10px 12px;border:1px solid #bbb;border-radius:6px;background:#fafafa;cursor:pointer;font-size:15px}
 .opt:hover{background:#f0f0f0}
 .opt.correct{background:#d8f5d8;border-color:#2e9e2e}
 .opt.wrong{background:#f7d6d6;border-color:#c23b3b}
 .opt:disabled{cursor:default}
 .fb{margin-top:10px;font-weight:600;min-height:22px}
 .next{margin-top:12px;padding:8px 16px;font-size:15px;cursor:pointer}
 #summary{display:none;font-size:18px;font-weight:700;margin-top:20px}
</style></head><body>
<h1>__TITLE__</h1>
<div class="bar">Score: <span id="score">0</span> / <span id="answered">0</span></div>
__CARDS__
<button class="next" id="next">Next &#9654;</button>
<div id="summary"></div>
<script>
 const cards=[...document.querySelectorAll('.card')];let cur=0,score=0,answered=0;
 const scoreEl=document.getElementById('score'),ansEl=document.getElementById('answered');
 const nextBtn=document.getElementById('next'),summary=document.getElementById('summary');
 function show(i){cards.forEach((c,k)=>c.classList.toggle('active',k===i));}
 cards.forEach(card=>{
   card.querySelectorAll('.opt').forEach(opt=>{
     opt.addEventListener('click',()=>{
       if(card.dataset.done)return;card.dataset.done='1';
       const correct=card.querySelector('.opt[data-correct]');
       card.querySelectorAll('.opt').forEach(o=>{o.disabled=true;if(o.dataset.correct)o.classList.add('correct');});
       const ok=opt.dataset.correct==='1';if(!ok)opt.classList.add('wrong');
       answered++;if(ok)score++;scoreEl.textContent=score;ansEl.textContent=answered;
       card.querySelector('.fb').textContent=ok?'\\u2713 Correct':('\\u2717 Correct: '+correct.textContent.replace(/^[A-D]\\. /,''));
     });
   });
 });
 nextBtn.addEventListener('click',()=>{
   if(cur<cards.length-1){cur++;show(cur);}
   else{cards.forEach(c=>c.classList.remove('active'));nextBtn.style.display='none';
     summary.style.display='block';
     summary.textContent='Done \\u2014 '+score+' / '+cards.length+'  ('+Math.round(100*score/Math.max(cards.length,1))+'%)';}
 });
 document.addEventListener('keydown',e=>{const m={a:0,b:1,c:2,d:3};if(e.key in m){const c=cards[cur];if(c){const b=c.querySelectorAll('.opt')[m[e.key]];if(b)b.click();}}});
 if(cards.length)show(0);
</script></body></html>"""


def _mask_highlight(img, bbox):
    from PIL import ImageDraw
    W, H = img.size
    x, y = int(bbox[0] * W), int(bbox[1] * H)
    w, h = int(bbox[2] * W), int(bbox[3] * H)
    pad = max(3, int(0.005 * W))
    box = [x - pad, y - pad, x + w + pad, y + h + pad]
    d = ImageDraw.Draw(img)
    d.rectangle(box, fill=(238, 238, 238))                       # blank the label text
    d.rectangle(box, outline=(214, 40, 40), width=max(2, int(0.004 * W)))  # highlight
    d.text(((box[0] + box[2]) // 2 - 4, (box[1] + box[3]) // 2 - 8), "?", fill=(214, 40, 40))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    result = {"success": False, "html_path": args.out, "question_count": 0, "error": None}
    try:
        from PIL import Image
        raw = sys.stdin.buffer.read().decode("utf-8-sig").strip()
        if not raw:
            raise ValueError("no quiz-spec on stdin")
        spec = json.loads(raw)
        title = spec.get("title") or "LearnKit image quiz"
        questions = spec.get("questions") or []

        # validate so the rendered total is accurate. A question with no
        # image_path is a text-only card (img=None). A question that names an
        # image which is missing/unreadable is a broken reference → skipped.
        valid = []
        for q in questions:
            ip = q.get("image_path")
            if ip:
                if not os.path.exists(ip):
                    continue
                try:
                    img = Image.open(ip).convert("RGB")
                except Exception:
                    continue
            else:
                img = None
            valid.append((q, img))

        total = len(valid)
        cards = []
        for idx, (q, img) in enumerate(valid):
            if img is not None:
                crop_bbox = q.get("crop_bbox")
                if crop_bbox:
                    img = crop_norm(img, crop_bbox)
                target_bbox = q.get("target_bbox")
                if target_bbox:
                    _mask_highlight(img, target_bbox)
                uri = data_uri(img)
            opts = q.get("options") or []
            ai = int(q.get("answer_index", 0))
            btns = []
            for k, opt in enumerate(opts):
                correct = ' data-correct="1"' if k == ai else ''
                letter = "ABCD"[k] if k < 4 else str(k + 1)
                btns.append(BTN_TMPL.format(correct=correct, letter=letter,
                                            text=htmllib.escape(str(opt))))
            stem = htmllib.escape(q.get("stem") or "What is the name of the highlighted structure?")
            if img is not None:
                cards.append(CARD_TMPL.format(i=idx, n=idx + 1, total=total, uri=uri,
                                              stem=stem, buttons="\n".join(btns)))
            else:
                cards.append(CARD_TMPL_NOIMG.format(i=idx, n=idx + 1, total=total,
                                                    stem=stem, buttons="\n".join(btns)))

        page = (PAGE_TMPL
                .replace("__TITLE__", htmllib.escape(title))
                .replace("__CARDS__", "\n".join(cards)))
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(page)
        result["question_count"] = total
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)

    print(json.dumps(result))  # ASCII-safe stdout


if __name__ == "__main__":
    main()
