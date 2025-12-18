# GitBook Template for ScreenSteps Exporter

This template exports ScreenSteps documentation in GitBook-compatible format, following the [GitBook directory structure](https://gitbook-ng.github.io/structure.html).

## GitBook Structure

GitBook uses a simple, standardized directory structure:

```
.
├── README.md           # Introduction/Preface (required)
├── SUMMARY.md          # Table of Contents (optional but recommended)
├── chapter-1/
│   ├── README.md       # Chapter introduction
│   └── article-1.md    # Articles in the chapter
└── chapter-2/
    ├── README.md
    └── article-2.md
```

## Usage

Export with the GitBook template:

```bash
python ss_exporter.py -n YOUR_ACCOUNT -u YOUR_USER -p YOUR_TOKEN \
  -t samples/gitbook_template \
  -o ./output \
  -s SITE_ID \
  -g
```

**Important:** Use the `-g` (or `--group-by-topic`) flag to organize articles by chapter/topic into separate folders, which is required for proper GitBook structure.

## Template Structure

```
gitbook_template/
  README.md              # Manual introduction template
  SUMMARY.md             # Table of contents template
  @article/
    @article.md          # Article content template
    images/
      @images            # Marker for image files
    attachments/
      @attachments       # Marker for attachment files
```

## Output Structure

When you export using this template with `-g` flag, you'll get:

```
output/
  Site Name/
    README.md            # Introduction (from manual title)
    SUMMARY.md           # Table of contents with all chapters and articles
    Chapter 1/
      README.md          # Chapter introduction (optional)
      Article 1.md
      Article 2.md
      images/
        image1.jpg
    Chapter 2/
      README.md
      Article 3.md
      attachments/
        file.pdf
```

This structure is ready to be used with GitBook by running:

```bash
gitbook init
gitbook serve
```

## Template Variables

### In README.md:
- `{{title}}` - Manual title

### In SUMMARY.md:
- `{{chapter}}...{{chapter}}` - Chapter block (repeats for each chapter)
- `{{title}}` - Chapter/article title
- `{{article}}...{{article}}` - Article block (repeats for each article in chapter)
- `{{link}}` - Relative link to article file

### In @article.md:
- `{{title}}` - Article title
- `{{html}}` - Article content (auto-converted to Markdown)
- `{{id}}` - Article ID
- `{{manual_id}}` - Parent manual ID
- `{{chapter_id}}` - Parent chapter ID
- `{{last_edited_by}}` - Last editor
- `{{last_edited_at}}` - Last edit timestamp
- `{{meta_title}}` - SEO title
- `{{meta_description}}` - SEO description
- `{{created_at}}` - Creation timestamp

## Features

- ✅ GitBook-compatible directory structure
- ✅ Automatic `SUMMARY.md` generation with proper linking
- ✅ Chapter-based folder organization (with `-g` flag)
- ✅ Markdown conversion from HTML
- ✅ Image and attachment handling
- ✅ Relative path linking
- ✅ Clean, readable filenames

## Example SUMMARY.md Output

```markdown
# Summary

## Getting Started
* [Installation](Getting Started/Installation.md)
* [Configuration](Getting Started/Configuration.md)

## User Guide
* [Creating Projects](User Guide/Creating Projects.md)
* [Managing Files](User Guide/Managing Files.md)
```

## Notes

- The `-g` flag is **required** for proper GitBook structure
- Use `title` naming (default) for readable folder and file names
- Images and attachments are placed relative to their articles
- The exporter automatically converts HTML to clean Markdown
- All internal links in SUMMARY.md use relative paths

## Customization

You can customize the templates:

1. **README.md** - Add more introduction text or metadata
2. **SUMMARY.md** - Modify the structure or add custom sections
3. **@article.md** - Change article layout, add metadata, custom formatting

## Building Your GitBook

After exporting, navigate to the output folder and run:

```bash
# Initialize GitBook (if needed)
gitbook init

# Serve locally for preview
gitbook serve

# Build HTML
gitbook build

# Or build PDF/ebook
gitbook pdf
gitbook epub
gitbook mobi
```

## See Also

- [GitBook Documentation](https://gitbook-ng.github.io/)
- [GitBook Directory Structure](https://gitbook-ng.github.io/structure.html)
- [GitBook Pages and Summary](https://gitbook-ng.github.io/pages.html)
