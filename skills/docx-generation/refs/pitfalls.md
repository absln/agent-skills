# DOCX Generation Pitfalls — Case Studies

Case studies of real failures encountered when generating .docx documents programmatically.

## Case 1: Word "Experienced an Error" on Opening (Node docx v9.7.1)

### Symptoms
- File generated successfully, appears on disk with reasonable size
- Word shows generic error dialog: "Word experienced an error trying to open the file"
- No specific error code or line number

### Root Causes (multi-layered)

**Cause A: Missing `type` on ImageRun**
- Node docx v9 `ImageRun` constructor has a `type` parameter that defaults to undefined
- Without `type: "png"`, the image file inside the zip gets extension `.undefined`
- Word cannot identify the file format → fails to render → generic error
- Fix: Always pass `type: "png"` (or `"jpg"`/`"gif"` matching the actual format)

**Cause B: Duplicate r:embed references**
- Reusing the same `ImageRun` object across multiple paragraph children
- Each reuse generates a new `<w:drawing>` with the same `r:embed` ID
- Result: 2x `r:embed` count vs relationship count (34 images → 68 embeds)
- Word may silently handle this in some versions, fail in others
- Fix: Create a new `ImageRun` for each insertion point

**Cause C: Empty zip directory entries**
- Node docx sometimes writes a zero-size `word/media/` directory entry
- Strict OOXML parsers reject directory entries in the zip bag
- Fix: Switch to python-docx which doesn't produce these

### Verification Commands

```bash
# Check for empty directory entries
node -e "
const z = new (require('adm-zip'))('output.docx');
z.getEntries().forEach(e => {
  if (e.entryName === 'word/media/' && e.isDirectory)
    console.log('FOUND empty media dir entry — file may be broken');
});
"

# Check embed vs relationship count
node -e "
const z = new (require('adm-zip'))('output.docx');
const xml = z.readAsText('word/document.xml');
const embeds = (xml.match(/r:embed=\"rId\d+\"/g) || []).length;
const rels = z.readAsText('word/_rels/document.xml.rels');
const images = (rels.match(/\/image\"/g) || []).length;
console.log('Embeds:', embeds, 'Image rels:', images, 'Match:', embeds === images);
"
```

## Case 2: PIL RGBA Image Causing Black Background

### Symptoms
- PNG screenshots with transparency appear with black background after Pillow save
- Only affects RGBA mode images

### Root Cause
`img.save(buf, format="PNG")` on an RGBA image with default PNG settings may not preserve alpha correctly. Converting to RGB discards alpha but doesn't set a white matte.

### Fix
```python
if img.mode in ("RGBA", "P"):
    # Create white background first
    background = Image.new("RGB", img.size, (255, 255, 255))
    if img.mode == "RGBA":
        background.paste(img, mask=img.split()[3])  # use alpha as mask
    else:
        background.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[3])
    img = background
```

Simpler fix for most screenshots (no real alpha needed):
```python
if img.mode in ("RGBA", "P"):
    img = img.convert("RGB")
```

## Case 3: Chinese Characters Not Rendering

### Symptoms
- Chinese text appears as squares/boxes in generated docx
- Western text renders normally

### Root Cause
In OOXML, fonts have two axes: `w:ascii`/`w:hAnsi` (Western) and `w:eastAsia` (CJK). Setting only `font.name` defaults to the Western axis.

### Fix (python-docx)
```python
run.font.name = "SimSun"
run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
```

### Fix (Node docx)
```javascript
new TextRun({
  text: "中文",
  font: { name: "SimSun" },
  // docx v9 may require custom XML for eastAsia
})
```

## Case 4: TOC Not Updating

### Symptoms
- TOC shows placeholder text or "No table of contents entries found"
- Document opens but TOC field hasn't been computed

### Root Cause
`TOC` is a Word field that must be updated before display. python-docx and Node docx only insert the field code, not the computed result.

### Fix
1. Tell user: "Open in Word, right-click the TOC and select Update Field, or press Ctrl+A then F9"
2. OR: Use Word COM automation to force-update:
```python
word = win32.Dispatch("Word.Application")
doc = word.Documents.Open(path)
doc.Fields.Update()
doc.Save()
doc.Close()
```

## Case 5: File Size Too Large (50+ MB)

### Symptoms
- 30 screenshots at native resolution → 50+ MB docx
- Word opens slowly or fails on low-memory machines

### Root Cause
Original screenshots are 1920×1080 or larger, saved at high quality by Windows Snipping Tool.

### Fix
Compress to max 800-900 px width before embedding. The difference in visible quality at 12 cm print width is negligible.

| Resolution | Per image | 30 images total |
|-----------|-----------|-----------------|
| 1920×1080 (original) | 1-2 MB | 30-50 MB |
| 900×506 (compressed) | 100-400 KB | 3-12 MB |
| 600×338 (aggressive) | 50-150 KB | 1.5-4.5 MB |

## Resolution Protocol

When a generated docx fails to open:

1. Run XML well-formedness check on `word/document.xml`
2. Verify `r:embed` count == image relationship count
3. Check for `undefined`/`NaN` in XML
4. Check for empty zip directory entries
5. If all above pass, open with Word COM to get the real error
