from pprint import pprint
from jinja2 import Environment, FileSystemLoader, select_autoescape
import datetime as dt

SUCCESS = "✅"
WARNING = "⚠️"
FAILURE = "❌"

# Set up Jinja environment
template_dir = 'templates'  # Directory where your templates are stored
env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=select_autoescape(['html', 'xml', 'css'])  # Enable autoescaping for HTML/XML templates
)

# Load a specific template
template = env.get_template('index.html')  # Replace with your template file name

t = {
    "test_name": "tests.BasicUbuntu.test_snap_preseed_optimized",
    "runs": [
        {
            "url": "/", 
            "config_string": "amd64-blah",
            "error_log": """ERROR: AMD64 blew up for some reason...

            Lorem ipsum dolor sit amet, qui minim labore adipisicing minim sint cillum sint consectetur cupidatat. Lorem ipsum dolor sit amet, qui minim labore adipisicing minim sint cillum sint consectetur cupidatat. Lorem ipsum dolor sit amet, qui minim labore adipisicing minim sint cillum sint consectetur cupidatat."""
        },
        {
            "url": "/", 
            "config_string": "arm64-blah",
            "error_log": """ERROR: ARM64 has some terrible thing happen to it. 

            Lorem ipsum dolor sit amet, officia excepteur ex fugiat reprehenderit enim labore culpa sint ad nisi Lorem pariatur mollit ex esse exercitation amet. Nisi anim cupidatat excepteur officia. Reprehenderit nostrud nostrud ipsum Lorem est aliquip amet voluptate voluptate dolor minim nulla est proident. Nostrud officia pariatur ut officia. Sit irure elit esse ea nulla sunt ex occaecat reprehenderit commodo officia dolor Lorem duis laboris cupidatat officia voluptate. Culpa proident adipisicing id nulla nisi laboris ex in Lorem sunt duis officia eiusmod. Aliqua reprehenderit commodo ex non excepteur duis sunt velit enim. Voluptate laboris sint cupidatat ullamco ut ea consectetur et est culpa et culpa duis."""
        },
    ]
}

j = {
    "suite": "Jammy",
    "family": "Base",
    "build_job_info": {"result": "SUCCESS"},
    "upload_job_info": {"result": "SUCCESS"},
    "test_job_info": {
        "result": "UNSTABLE",
        "matrix_results": {
            "success": 111,
            "unstable": 222,
            "failure":333
        }
    },
    "test_failures": [t,t,t]
}

oracle = {
    "name": "Oracle",
    "pipeline_runs": [j,j,j]
}

ibm = {
    "name": "IBM",
    "pipeline_runs": [j,j]
}


# Define template context data
context = {
    'timestamp': dt.datetime.now(),
    'projects': [ibm, oracle]
}



# Render template with context
rendered_output = template.render(context)

# Print or use the rendered template output
print(rendered_output)

# Render a template with provided context and write it to a file
def render_template_to_file(template_name, context, output_file):
    template = env.get_template(template_name)
    output = template.render(context)
    
    # Write the rendered template to a file
    with open(output_file, 'w') as file:
        file.write(output)
    print(f"Template rendered and saved to {output_file}")

# import pre_html
# context = pre_html.html_report

#
# render_template_to_file(
#     template_name="index.html",
#     context=context,
#     output_file="index.html"
# )
