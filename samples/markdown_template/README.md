# Markdown Template for ScreenSteps Exporter

This template exports ScreenSteps documentation as clean Markdown files.

## Usage

```bash
python ss_exporter.py -n YOUR_ACCOUNT -u YOUR_USER -p YOUR_TOKEN \
  -t samples/markdown_template \
  -o ./output \
  -s SITE_ID
```

## Template Structure

```
markdown_template/
  @toc.md                    # Table of contents template
  articles/
    @article/
      @article.md            # Article content template
      images/
        @images              # Marker for image files
      attachments/
        @attachments         # Marker for attachment files
```

## Features

- Exports articles as `.md` (Markdown) files
- Converts HTML content to clean Markdown
- Uses document titles for filenames (not IDs)
- Preserves folder structure
- Downloads and references images and attachments

## Template Variables

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

### In @toc.md:
- `{{title}}` - Manual/chapter title
- `{{chapter}}...{{chapter}}` - Chapter block
- `{{article}}...{{article}}` - Article block
- `{{link}}` - Link to article (within article block)

## Output Structure

```
output/
  Site Name/
    Manual Name.md           # Table of contents
    articles/
      Article Name/
        Article Name.md      # Article content
        images/
          image1.jpg
          image2.png
        attachments/
          file.pdf
```

## Notes

- By default, the exporter uses `title` naming (human-readable names)
- Images and attachments are downloaded and linked with relative paths
- The `{{html}}` placeholder is automatically converted from HTML to Markdown
