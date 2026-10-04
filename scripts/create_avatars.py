#!/usr/bin/env python3
"""Create the original VNizer guide as editable vector assets."""

from pathlib import Path

EXPRESSIONS = {
    "neutral": '<path d="M216 270 Q240 282 264 270"/>',
    "explaining": '<ellipse cx="240" cy="275" rx="15" ry="10"/>',
    "curious": '<path d="M215 277 Q237 266 263 277"/><path d="M179 208 L209 200"/>',
    "positive": '<path d="M212 268 Q240 300 268 268 Z" fill="#e58d9c"/>',
    "serious": '<path d="M216 278 L264 278"/><path d="M179 205 L209 211 M270 211 L300 205"/>',
}


def main():
    target = Path(__file__).resolve().parents[1] / "src/vnizer/assets"
    target.mkdir(parents=True, exist_ok=True)
    for mood, expression in EXPRESSIONS.items():
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="640" viewBox="0 0 480 640">
<title>VNizer guide: {mood}</title>
<ellipse cx="240" cy="612" rx="168" ry="18" fill="#102032" opacity=".15"/>
<path d="M112 274 Q75 88 236 72 Q414 81 365 326 L334 427 H140Z" fill="#24364e"/>
<path d="M167 368 Q101 381 87 487 L73 614 H407 L393 487 Q379 381 312 368Z" fill="#327c86"/>
<path d="M193 356 L192 396 L240 447 L288 396 L287 356" fill="#edb69b"/>
<path d="M166 369 L190 382 L240 447 L207 468 L156 407Z M314 369 L290 382 L240 447 L273 468 L324 407Z" fill="#e5f2ee"/>
<path d="M148 164 Q239 109 332 164 L326 270 Q308 350 240 366 Q172 350 154 270Z" fill="#f3c6ad"/>
<path d="M129 195 Q126 93 244 94 Q356 101 350 204 Q297 181 271 132 Q247 185 129 211Z" fill="#24364e"/>
<path d="M133 220 Q119 311 158 365 L176 319 L156 211Z M345 198 Q365 298 324 358 L310 313 L329 197Z" fill="#24364e"/>
<ellipse cx="196" cy="234" rx="12" ry="17" fill="#234456"/>
<ellipse cx="283" cy="234" rx="12" ry="17" fill="#234456"/>
<circle cx="200" cy="229" r="4" fill="white"/><circle cx="287" cy="229" r="4" fill="white"/>
<path d="M236 244 L232 259 L242 259" stroke="#cd917d" stroke-width="3" fill="none"/>
<g stroke="#704b49" stroke-width="4" fill="none" stroke-linecap="round">{expression}</g>
<path d="M298 153 L325 178 M304 145 L332 170" stroke="#70d7c2" stroke-width="7"/>
<path d="M119 468 L116 578 L190 574 L200 610 H87 M361 468 L364 578 L292 574 L283 610 H393" fill="#296c78"/>
<path d="M159 486 L234 503 L316 481 L320 574 L239 601 L164 578Z" fill="#ecdfbb" stroke="#cbbb96" stroke-width="3"/>
<path d="M234 503 L239 601" stroke="#b8a67d" stroke-width="3"/>
<path d="M120 566 Q145 538 174 560 L189 586 L163 600 L120 590Z M363 566 Q337 538 309 560 L293 586 L319 600 L363 590Z" fill="#f3c6ad"/>
</svg>
'''
        (target / f"{mood}.svg").write_text(svg)


if __name__ == "__main__":
    main()
