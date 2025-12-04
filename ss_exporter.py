#!/usr/bin/env python3

import ssl
import sys, getopt
import requests
import time
import json
import os, fnmatch
import re
import shutil
from urllib.parse import urlparse
import html2text

def html_to_markdown(html_content):
    if not html_content:
        return ''
    
    h = html2text.HTML2Text()
    h.body_width = 0
    h.mark_code = True
    
    markdown = h.handle(html_content)
    
    import re
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    
    # Convert [code] tags to proper markdown code blocks
    markdown = re.sub(r'\[code\]\s*\n', '```\n', markdown)
    markdown = re.sub(r'\n\s*\[/code\]', '\n```', markdown)
    
    # Remove "Click to copy" text that follows code blocks
    markdown = re.sub(r'```\s*\n\s*Click to copy\s*\n', '```\n\n', markdown)
    
    # Remove link wrapping around images: [ ![alt](image.png) ](image.png) -> ![alt](image.png)
    markdown = re.sub(r'\[\s*(!\[.*?\]\([^)]*\))\s*\]\([^)]*\)', r'\1', markdown)
    
    return markdown.strip()

# globals
article_file_indicator = '@article.*'
manual_file_indicator = '@toc.*'
summary_file_indicator = 'SUMMARY.*'
image_folder_indicator = '@images'
attach_folder_indicator = '@attachments'

# these are the handlebars you can use in an article file
article_handlebars = [
    "id",
    "title",
    "manual_id",
    "chapter_id",
    "last_edited_by",
    "last_edited_at",
    "meta_title",
    "meta_description",
    "meta_search",
    "created_at"]

# these are the handlebars you can use in manual file
# {{title}} outside of any blocks for manual title
# {{chapter}} to start and end the chapter, then {{title}} in the block
# {{article}} to start and end the manual, then {{title}} and {{link}} in the block

# Define the help message here.
def print_help():
    print("""
    Usage:
    run -n <account_name> -u <user_id> -p <token_password>
    [-t <template_folder>]
    [-o <output_folder>]
    [-s <site_id>]
    [-m <manual_id>]
    [-a <article_id>]
    [-M <manual_file_name]
    [-i object_identifier]
    [-g] (--group-by-topic)

    Explanations:
    -n This is used for the name of the account (http://<account_name>.screenstepslive.com)
    -u Your user ID
    -p Your API token or password
    -t The folder with your templates (optional)
    -o The folder you would like with outputs (optional)
    -s If you'd like to only download one site, specify the ID here (optional)
    -m If you'd like to only download one manual, specify the ID here (optional)
    -a If you'd like to only download one article, specify the ID here (optional)
    -M Pass in a specific name to use for the manual file. Must pass in the -m parameter.
    -i Specifies how the site, manual, and article files should be named. By default the "title" is used. You can set this to "id" or "title_id". "title_id" will use the name with " [ID]" appended to the end.
    -g Group articles by their topic/chapter in separate folders (optional)

    Examples:
    run -n customerknowledge -u mikey -p mypassword -s 15226
    run -n myaccount -u johnsmith -p notAgoodPassword -a 21234
    """)

def make_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_file(directory, url):
    short_path = url.split('/')[-1].split('?')[0]
    local_filename = os.path.join(directory, short_path)
    r = requests.get(url, stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    return short_path

def find_file(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

def find_dirs(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for dirname in dirs:
            if pattern in dirname.split():
                result.append(os.path.join(root, dirname))
    return result

def split_path(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

def remove_list_overlap(larger,smaller):
    for myitem in smaller:
        if myitem in larger:
            larger.remove(myitem)
    return larger

def find_relative_path(thispath,template_folder):
    relative_path = remove_list_overlap(split_path(thispath),split_path(template_folder))
    if len(relative_path[:-1]) > 0:
        relative_path = os.path.join(*relative_path[:-1])
    else:
        relative_path = ''
    return relative_path

def find_at_file_path(thispath,template_folder):
    relative_path = remove_list_overlap(split_path(thispath),split_path(template_folder))
    return os.path.join(*relative_path)

def remove_directory(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)

def remove_directories(directories):
    for directory in directories:
        remove_directory(directory)

def remove_found_files(files):
    for name in files:
        if os.path.exists(name):
            os.remove(name)

def write_file(directory, name, rawtext):
    with open(os.path.join(directory, name), 'wb+') as f:
        f.write(rawtext.encode('utf-8'))

def copy_and_overwrite(from_path, to_path):
    if os.path.exists(to_path):
        shutil.rmtree(to_path)
    shutil.copytree(from_path, to_path)

def read_file(path):
    with open(path) as f:
        contents = f.read()
    return contents

def _decode(var):
    # all strings are unicode now
    return str(var)

def prepare_for_filename(string):
        # Convert to lowercase and replace spaces/special chars with hyphens (kebab-case)
        # Remove special characters, keep only alphanumeric and spaces
        cleaned = "".join([c if c.isalnum() or c.isspace() else ' ' for c in string])
        # Replace multiple spaces with single space, strip, then convert to lowercase with hyphens
        kebab = '-'.join(cleaned.split()).lower()
        return kebab

def get_manual_parent_folder(manual_title):
        """Determine the parent folder based on manual name"""
        manual_lower = manual_title.lower()
        
        # Resources manuals
        if 'faq' in manual_lower or 'release' in manual_lower or 'misc' in manual_lower:
            return 'resources'
        # Everything else goes to documentations
        else:
            return 'documentations'

def get_chapter_path_with_nesting(chapter_title):
        """Determine if a chapter should be nested and return the path"""
        chapter_lower = chapter_title.lower()
        
        # SharinPix Features subcategories should be nested
        if 'sharinpix features' in chapter_lower:
            # Extract the subcategory part after the dash
            if ' - ' in chapter_title:
                parts = chapter_title.split(' - ', 1)
                parent = prepare_for_filename(parts[0])  # sharinpix-features
                child = prepare_for_filename(parts[1])   # the subcategory
                return parent + '/' + child
        
        return prepare_for_filename(chapter_title)

def calculate_relative_path(from_path, to_path):
        """Calculate relative path from one article to another"""
        # Split paths into parts
        from_parts = from_path.split('/')
        to_parts = to_path.split('/')
        
        # Remove filename from from_path (keep only directory parts)
        from_dir_parts = from_parts[:-1]
        
        # Find common prefix
        common_length = 0
        for i in range(min(len(from_dir_parts), len(to_parts) - 1)):
            if from_dir_parts[i] == to_parts[i]:
                common_length += 1
            else:
                break
        
        # Calculate how many levels to go up
        levels_up = len(from_dir_parts) - common_length
        
        # Build the relative path
        if levels_up > 0:
            relative = '../' * levels_up + '/'.join(to_parts[common_length:])
        else:
            # Same directory or subdirectory
            relative = '/'.join(to_parts[common_length:])
        
        return relative

def _print(var):
    return var

def main(argv):
    # Define variables we need.
    site_name = '' #n / site_name
    user_id = ''#u / user_id
    api_token = ''#p / password
    template_folder = '' #t / template
    output_folder = '' #o / output
    site_id = ''#s / site
    manual_id = ''#m / manual
    article_id = ''#a / article
    manual_file_name = ''#M / manual_file_name
    object_identifier = 'title'#i / object_identifier - default to 'title' for name-based exports
    group_by_topic = False#g / group articles by topic/chapter
    try:
        opts, args = getopt.getopt(argv,"hn:u:p:t:o:s:m:a:M:i:g",["site_name=","user_id=","password=","template_folder=","output_folder=","site_id=","manual_id=","article_id=","manual_file_name=","object_identifier=","group-by-topic"])
    except getopt.GetoptError:
        print('use "run.py -h" for help')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_help()
            sys.exit()
        elif opt in ("-n", "--site_name"):
            site_name = arg
        elif opt in ("-u", "--user_id"):
            user_id = arg
        elif opt in ("-p", "--password"):
            api_token = arg
        elif opt in ("-t", "--template_folder"):
            template_folder = arg
        elif opt in ("-o", "--output_folder"):
            output_folder = arg
        elif opt in ("-s", "--site_id"):
            site_id = arg
        elif opt in ("-m", "--manual_id"):
            manual_id = arg
        elif opt in ("-a", "--article_id"):
            article_id = arg
        elif opt in ("-M", "--manual_file_name"):
            if manual_id != "":
                manual_file_name = arg
        elif opt in ("-i", "--object_identifier"):
            object_identifier = arg
        elif opt in ("-g", "--group-by-topic"):
            group_by_topic = True


    # check if required attributes exist
    if (site_name == '') or (user_id == '') or (api_token == ''):
        print("Site_name, user_id, and password are required. Try 'run -h' if you need help.")
        sys.exit()

    # if the output isn't specified, just put it in their home directory
    if (output_folder == ''):
        output_folder = os.path.expanduser('~')

    # if the template folder isn't specified, we'll just print out html files, otherwise we
    # have some prep work to do.
    if (template_folder == ''):
        template_specified = False
        is_article_folder = False
        is_manual_files = False
        is_image_folder = False
        is_attach_folder = False
        print("Warn: Template folder not specified.  Will output Markdown files only.")
    else:
        # check if template folder exists
        if os.path.exists(template_folder):
            template_specified = True

            # check if folder has an @article folder
            at_article_folder = find_dirs("@article",template_folder)

            if len(at_article_folder) == 0:
                print("Info: No @article folder found.")
                is_article_folder = False
            elif len(at_article_folder) == 1:
                at_article_folder = at_article_folder[0]
                print("Info: Template folder has @article folder. "  + _decode(at_article_folder))
                is_article_folder = True
            else:
                print("Error: More than one @article folder found.")
                sys.exit()

            # check if folder has an @images folder
            at_images_folder = find_file(image_folder_indicator,template_folder)

            if len(at_images_folder) == 0:
                print("Info: No " + image_folder_indicator + " file found.")
                is_image_folder = False
            elif len(at_images_folder) == 1:
                at_images_folder = find_at_file_path(os.path.dirname(at_images_folder[0]),template_folder)
                print("Info: Template folder has " + image_folder_indicator + " file. "  + _print(at_images_folder))
                is_image_folder = True
            else:
                print("Error: More than one " + _print(image_folder_indicator) + " file found.")
                sys.exit()

            # check if folder has an @attachments folder
            at_attach_folder = find_file(attach_folder_indicator,template_folder)

            if len(at_attach_folder) == 0:
                print("Info: No " + attach_folder_indicator + " file found.")
                is_attach_folder = False
            elif len(at_attach_folder) == 1:
                at_attach_folder = find_at_file_path(os.path.dirname(at_attach_folder[0]),template_folder)
                print("Info: Template folder has " + attach_folder_indicator + " file. "  + _print(at_attach_folder))
                is_attach_folder = True
            else:
                print("Error: More than one " + attach_folder_indicator + " file found.")
                sys.exit()

            # now let's see if there are @article file(s). we'll take as many
            # as you want, as long as there is at least one!
            at_article_file = find_file(article_file_indicator,template_folder)

            if at_article_file == []:
                print("Error: No @article file found.")
                sys.exit()

            # ok, phew we found at least one
            else:
                print("Info: @article file(s) found.")

                # read in template data
                article_files = {}
                for each_article_file in at_article_file:
                    article_files[each_article_file] = read_file(each_article_file)

            # now let's check if theres a manual file
            at_manual_file = find_file(manual_file_indicator,template_folder)
            at_summary_file = find_file(summary_file_indicator,template_folder)

            if at_manual_file == [] and at_summary_file == []:
                print("Warn: No @toc or SUMMARY file found.")
                is_manual_files = False
            else:
                # Prefer SUMMARY file if both exist
                if at_summary_file != []:
                    print("Info: SUMMARY file(s) found (GitBook format).")
                    at_manual_file = at_summary_file
                else:
                    print("Info: @toc file(s) found.")
                is_manual_files = True

                # read in template data
                manual_files = {}
                manual_files_ref = {}

                for each_manual_file in at_manual_file:
                    manual_files[each_manual_file] = read_file(each_manual_file)

                    # Each @manual file consists of pre-chapter block, chapter block, and post-chapter block
                    # the chapter block then consists of the pre-article block, the article block, and post-article block
                    chapter_split = re.split('{{chapter}}',manual_files[each_manual_file])

                    if len(chapter_split) < 3:
                        chapter_split = ['',chapter_split[0],'']

                    article_split = re.split('{{article}}',chapter_split[1])

                    if len(article_split) < 3:
                        add_end_manual_file = article_split[0]
                        article_split = ['','','']
                    else:
                        add_end_manual_file = ''

                    manual_files_ref[each_manual_file] = [
                                                chapter_split[0], # 0 - pre-chapter
                                                article_split[0], # 1 - pre-article (chapter)
                                                article_split[1], # 2 - article
                                                article_split[2], # 3 - post-article (chapter)
                                                chapter_split[2]] # 4 - post-chapter

        # template folder didn't exist
        else:
            print("Error: Template folder not found. Try 'run -h' if you need help.")
            sys.exit()

    # set up request
    def screensteps_json(endpoint):
        base_url = 'https://' + site_name + '.screenstepslive.com/api/v2/'
        site_endpoint = base_url + endpoint
        try:
            while True:
                r = requests.get(site_endpoint, auth=(user_id, api_token))

                if r.status_code == 200:
                    return r.text
                elif r.status_code == 429:
                    # Rate limit exceeded
                    try:
                        retry_info = r.json()
                        retry_in = retry_info.get('retry_in', 60)  # Default to 60 seconds if not provided
                        print(f"Rate limit exceeded. Retrying in {retry_in} seconds...")
                        time.sleep(retry_in)
                    except ValueError:
                        # Failed to parse JSON, fall back to a default wait time
                        print("Rate limit exceeded. Retrying in 60 seconds (default)...")
                        time.sleep(60)
                else:
                    print('Error connecting to server (' + _decode(r.status_code) + ')')
                    sys.exit(2)
        except requests.exceptions.RequestException as e:
            print("Error connecting to server:", e)
            sys.exit(2)

    def screensteps(endpoint):
        rawtext = screensteps_json(endpoint)
        return json.loads(rawtext)

    # grab all sites for that user information
    print("> Pulling sites")
    sites = screensteps('sites') # grab sites
    print("> " + _print(str(sites)))

    # loop through sites
    for site in sites['sites']:
        this_site_id = _decode(site['id'])
        if (site_id == this_site_id) or (site_id == ''): # only action a site if site_id isn't set, or is a match
            print(">> Processing site: " + _print(site['title']))
            # print(">> " + _print(site))

            # folder for site - two paths 1) template folder, 2) no template folder
            if object_identifier == "title_id":
                site_folder = os.path.join(output_folder, prepare_for_filename(site['title']) + " [" + this_site_id + "]")
            elif object_identifier == "title":
                site_folder = os.path.join(output_folder, prepare_for_filename(site['title']))
            else:
                site_folder = os.path.join(output_folder, this_site_id)

            if template_specified:
                copy_and_overwrite(template_folder, site_folder)
            else:
                make_dir(site_folder)

            manuals = screensteps('sites/' + this_site_id) #grab manuals

            # loop through manuals
            for manual in manuals['site']['manuals']:
                this_manual_id = _decode(manual['id'])
                if (manual_id == this_manual_id) or (manual_id == ''): # only action a manual if manual isn't set, or is a match
                    print(">>> Processing manual: " + _print(manual['title']))
                    # print(">>> " + _print(manual))

                    if object_identifier == "title_id":
                        this_manual_identifier = prepare_for_filename(manual["title"]) + " [" + this_manual_id + "]"
                    elif object_identifier == "title":
                        this_manual_identifier = prepare_for_filename(manual["title"])
                    else:
                        this_manual_identifier = this_manual_id

                    chapters = screensteps('sites/' + this_site_id + '/manuals/' + this_manual_id) # grab chapters

                    # Determine parent folder for this manual's chapters
                    manual_parent_folder = get_manual_parent_folder(manual['title'])

                    # Create a mapping of article IDs to their file paths for link conversion
                    article_id_to_path = {}
                    # Store all article data for second pass processing
                    articles_data = []

                    print(">>> PASS 1: Fetching all articles and building link mapping...")
                    print(">>>> Manual parent folder: " + manual_parent_folder)
                    
                    # FIRST PASS: Build complete article ID to path mapping
                    for chapter in chapters['manual']['chapters']:
                        this_chapter_id = _decode(chapter['id'])
                        print(">>>> Mapping chapter: " + _print(chapter['title']))
                        
                        # Determine chapter folder name with potential nesting
                        if group_by_topic:
                            chapter_path = get_chapter_path_with_nesting(chapter['title'])
                            if object_identifier == "title_id":
                                chapter_path = chapter_path + "-" + this_chapter_id
                            
                            # Full path includes manual parent folder
                            chapter_folder_name = manual_parent_folder + '/' + chapter_path
                        else:
                            chapter_folder_name = ''
                        
                        articles = screensteps('sites/' + this_site_id + '/chapters/' + this_chapter_id)
                        
                        for article in articles['chapter']['articles']:
                            this_article_id = _decode(article['id'])
                            if (article_id == this_article_id) or (article_id == ''):
                                this_article = screensteps('sites/' + this_site_id + '/articles/' + this_article_id)
                                this_article_title = this_article['article']['title']
                                
                                if object_identifier == "title_id":
                                    this_article_identifier = prepare_for_filename(this_article_title) + " [" + this_article_id + "]"
                                elif object_identifier == "title":
                                    this_article_identifier = prepare_for_filename(this_article_title)
                                else:
                                    this_article_identifier = this_article_id
                                
                                # Build the relative path for link mapping
                                if group_by_topic:
                                    article_relative_link = chapter_folder_name + '/' + this_article_identifier + '.md'
                                else:
                                    article_relative_link = this_article_identifier + '.md'
                                
                                article_id_to_path[this_article_id] = article_relative_link
                                
                                # Store article data for second pass
                                articles_data.append({
                                    'article': this_article,
                                    'article_id': this_article_id,
                                    'article_identifier': this_article_identifier,
                                    'chapter_id': this_chapter_id,
                                    'chapter_title': chapter['title'],
                                    'chapter_folder_name': chapter_folder_name
                                })
                                
                                print(">>>>> Mapped article: " + _print(article['title']) + " -> " + article_relative_link)
                    
                    print(">>> PASS 2: Creating files with corrected links...")

                    # pre-chapter replaces on _decode(manual_files_ref[path][0])
                    if is_manual_files: # are there templates?
                        manual_files_temp = {}
                        for path, details in manual_files.items():
                            manual_files_temp[path] = []
                            manual_files_temp[path].append(_decode(manual_files_ref[path][0]).replace('{{title}}', chapters['manual']['title']))

                    # SECOND PASS: Process chapters and create files with correct links
                    # loop through chapters
                    for chapter in chapters['manual']['chapters']:
                        this_chapter_id = _decode(chapter['id'])
                        print(">>>> Processing chapter: " + _print(chapter['title']))
                        # print(">>>> " + _print(chapter))

                        # Create chapter folder if grouping by topic
                        if group_by_topic:
                            # Use the same logic as first pass for consistency
                            chapter_path = get_chapter_path_with_nesting(chapter['title'])
                            if object_identifier == "title_id":
                                chapter_path = chapter_path + "-" + this_chapter_id
                            
                            # Full path includes manual parent folder
                            chapter_folder_name = manual_parent_folder + '/' + chapter_path
                            
                            chapter_folder = os.path.join(site_folder, chapter_folder_name)
                            make_dir(chapter_folder)
                        else:
                            chapter_folder = site_folder

                        chapter['articles'] = []

                        # pre-article replaces on _decode(manual_files_ref[path][1])
                        if is_manual_files: # are there templates?
                            for path, details in manual_files.items():
                                manual_files_temp[path].append(_decode(manual_files_ref[path][1]).replace('{{title}}', chapter['title']))

                        # Process articles for this chapter from stored data
                        chapter_articles = [a for a in articles_data if a['chapter_id'] == this_chapter_id]
                        
                        for article_data in chapter_articles:
                            this_article = article_data['article']
                            this_article_id = article_data['article_id']
                            this_article_identifier = article_data['article_identifier']
                            
                            if (article_id == this_article_id) or (article_id == ''): # only action an article if article_id isn't set, or is a match
                                print(">>>>> Processing article: " + _print(this_article['article']['title']))

                                # Determine base folder for articles (chapter folder if grouping by topic, otherwise site folder)
                                base_folder = chapter_folder if group_by_topic else site_folder
                                
                                # For GitBook structure with -g flag, don't create article subfolders
                                if group_by_topic:
                                    # Articles go directly in chapter folder for GitBook
                                    article_folder = base_folder
                                elif is_article_folder:
                                    article_folder = os.path.join(base_folder, find_relative_path(at_article_folder,template_folder), this_article_identifier)
                                    copy_and_overwrite(at_article_folder, article_folder)
                                else:
                                    # write markdown to a file if no templates
                                    article_folder = base_folder

                                # Add to list of article ids and titles
                                chapter["articles"].append( {'id': this_article['article']['id'], 'title': this_article_identifier} )

                                # Convert HTML to Markdown
                                article_html = this_article['article']['html_body']
                                article_markdown = html_to_markdown(article_html)
                                
                                # Get current article's full path for calculating relative links
                                current_article_path = article_id_to_path[this_article_id]
                                
                                # Convert internal ScreenSteps links to markdown file references using complete mapping
                                # Pattern: https://docs.sharinpix.com/m/documentation/l/ARTICLE_ID or ../../documentation/l/ARTICLE_ID
                                for art_id, art_path in article_id_to_path.items():
                                    if art_id == this_article_id:
                                        continue  # Skip self-references
                                    
                                    # Calculate proper relative path from current article to target article
                                    if group_by_topic:
                                        relative_link = calculate_relative_path(current_article_path, art_path)
                                    else:
                                        relative_link = art_path
                                    
                                    # Handle both full URLs and relative paths
                                    article_markdown = re.sub(
                                        r'https?://[^/]+/m/documentation/l/' + re.escape(art_id) + r'[^)]*',
                                        relative_link,
                                        article_markdown
                                    )
                                    article_markdown = re.sub(
                                        r'\.\./\.\./documentation/l/' + re.escape(art_id) + r'[^)]*',
                                        relative_link,
                                        article_markdown
                                    )
                                    # Also handle /m/documentation/l/ paths
                                    article_markdown = re.sub(
                                        r'/m/documentation/l/' + re.escape(art_id) + r'[^)]*',
                                        relative_link,
                                        article_markdown
                                    )

                                # loop through attached files
                                this_articles_files = []
                                for content_block in this_article['article']['content_blocks']:
                                    if 'url' in content_block:

                                        # what type of file is it?
                                        download_ext = os.path.splitext(urlparse(content_block['url']).path)[1]
                                        if content_block['type'] == 'AttachmentContent': # attachment
                                            if group_by_topic:
                                                # GitBook: attachments at chapter level in .gitbook/assets
                                                files_folder = os.path.join(base_folder, '.gitbook', 'assets')
                                                short_files_folder = '.gitbook/assets'
                                                make_dir(files_folder)
                                            elif is_attach_folder:
                                                files_folder = os.path.join(base_folder,at_attach_folder)
                                                short_files_folder = at_attach_folder
                                                if '@article' in files_folder:
                                                    files_folder = files_folder.replace("@article", this_article_identifier)
                                                    short_files_folder = short_files_folder.replace("@article", this_article_identifier)
                                            else:
                                                files_folder = os.path.join(article_folder, 'attachments')
                                                short_files_folder = 'attachments'
                                                make_dir(files_folder)
                                        else: # image
                                            if group_by_topic:
                                                # GitBook: images at chapter level in .gitbook/assets
                                                files_folder = os.path.join(base_folder, '.gitbook', 'assets')
                                                short_files_folder = '.gitbook/assets'
                                                make_dir(files_folder)
                                            elif is_image_folder:
                                                files_folder = os.path.join(base_folder,at_images_folder)
                                                short_files_folder = at_images_folder
                                                if '@article' in files_folder:
                                                    files_folder = files_folder.replace("@article", this_article_identifier)
                                                    short_files_folder = short_files_folder.replace("@article", this_article_identifier)
                                            else:
                                                files_folder = os.path.join(article_folder, 'images')
                                                short_files_folder = 'images'
                                                make_dir(files_folder)

                                        print(">>>>>> Processing " + _print(content_block['type']) + ": " + _print(content_block['url']))
                                        new_file_path = download_file(files_folder,content_block['url'])
                                        this_articles_files.append([ _decode(content_block['url']), os.path.join(short_files_folder,new_file_path)])

                                article_files_paths = []
                                if template_specified:
                                    # step through each file that starts with "@article"
                                    for path, temp_html in article_files.items():

                                        back_dir = ''
                                        article_relative_path = find_relative_path(path,template_folder)
                                        temp_filename = this_article_identifier + os.path.splitext(path)[1]
                                        
                                        # For GitBook with -g flag, articles go directly in chapter folder
                                        if group_by_topic:
                                            # No subdirectory for articles in GitBook structure
                                            temp_filename = this_article_identifier + os.path.splitext(path)[1]
                                            back_dir = ''
                                        elif article_relative_path != '':
                                            article_relative_path = article_relative_path.replace("@article", this_article_identifier)
                                            temp_filename = os.path.join(article_relative_path,temp_filename)
                                            back_dir = '../' * len(split_path(article_relative_path))

                                        # find and replace {{html}} with markdown content
                                        temp_towrite = temp_html.replace("""{{html}}""",article_markdown)
                                        temp_towrite = temp_towrite.replace("""{{json}}""",json.dumps(this_article, sort_keys=True, indent=2, separators=(',', ': ')))

                                        # find and replace all the other handlebars specified
                                        for article_handlebar in article_handlebars:
                                            if article_handlebar != "link":
                                                temp_towrite = temp_towrite.replace(("{{" + _decode(article_handlebar) + "}}"), _decode(this_article['article'][article_handlebar]) )

                                        for this_articles_file in this_articles_files:
                                            # take off any query params
                                            image_url = this_articles_file[0].split("?", 1)[0]
                                            temp_towrite = temp_towrite.replace(image_url,(back_dir + this_articles_file[1].replace("\\", "/"))) # Fix windows paths
                                            # workaround: perform replace on thumbnail images
                                            thumbnail_url = image_url.replace("/original/", "/medium/")
                                            temp_towrite = temp_towrite.replace(thumbnail_url,(back_dir + this_articles_file[1].replace("\\", "/"))) # Fix windows paths

                                        # write file
                                        write_file(base_folder, temp_filename, temp_towrite)
                                        article_files_paths.append(temp_filename)
                                else:
                                    for this_articles_file in this_articles_files:
                                        article_markdown = article_markdown.replace(this_articles_file[0],this_articles_file[1].replace("\\", "/")) # Fix windows paths
                                    write_file(article_folder, (this_article_identifier + '.md'), article_markdown)
                                    article_files_paths.append((this_article_identifier + '.md'))

                                # article replaces on _decode(manual_files_ref[path][2])
                                if is_manual_files: # are there templates?
                                    article_handlebars.append("link")

                                    for path, details in manual_files.items():
                                        article_string = _decode(manual_files_ref[path][2])
                                        for article_handlebar in article_handlebars:
                                            if article_handlebar == "link":
                                                try:
                                                    same_ext_link = next(i for i in article_files_paths if os.path.splitext(i)[1] ==  os.path.splitext(path)[1])
                                                except:
                                                    print("Error: We didn't find a file extension match for the article from the TOC with: " + os.path.splitext(path)[1])
                                                    sys.exit()
                                                article_string = article_string.replace(("{{" + _decode(article_handlebar) + "}}"), same_ext_link)
                                            else:
                                                article_string = article_string.replace(("{{" + _decode(article_handlebar) + "}}"),_decode(this_article['article'][article_handlebar]))
                                        manual_files_temp[path].append(article_string)

                        # post-article replaces on _decode(manual_files_ref[path][3])
                        if is_manual_files: # are there templates?
                            for path, details in manual_files.items():
                                manual_files_temp[path].append(_decode(manual_files_ref[path][3]).replace('{{title}}',_decode(chapter['title'])))

                    # post-chapter replaces on _decode(manual_files_ref[path][4])
                    if is_manual_files: # are there templates?
                        for path, details in manual_files.items():
                            manual_files_temp[path].append(_decode(manual_files_ref[path][4]).replace('{{title}}',chapters['manual']['title']))

                            manual_relative_path = find_relative_path(path,template_folder)
                            if manual_relative_path == '':
                                manual_relative_path = site_folder
                            else:
                                manual_relative_path = os.path.join(site_folder,manual_relative_path)

                            # dump files
                            if manual_file_name != "":
                                temp_filename = manual_file_name + os.path.splitext(path)[1]
                            else:
                                temp_filename = this_manual_identifier + os.path.splitext(path)[1]
                            temp_file_contents = (''.join(manual_files_temp[path]) + add_end_manual_file)
                            temp_file_contents = temp_file_contents.replace("""{{json}}""", json.dumps(chapters, sort_keys=True, indent=2, separators=(',', ': ')))
                            write_file(manual_relative_path, temp_filename, temp_file_contents)

            # clean up the "@" files that we copied over for each site
            if template_specified:
                try:
                    remove_found_files(find_file(article_file_indicator,site_folder))
                    remove_found_files(find_file(manual_file_indicator,site_folder))
                    remove_found_files(find_file(summary_file_indicator,site_folder))
                    remove_found_files(find_file(image_folder_indicator,site_folder))
                    remove_found_files(find_file(attach_folder_indicator,site_folder))
                    remove_directories(find_dirs("@article", site_folder))
                except:
                    print("We had trouble deleting the copied template files.  You can ignore any extra files.")


if __name__ == "__main__":
    main(sys.argv[1:])
