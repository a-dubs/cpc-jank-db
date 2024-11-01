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
template = env.get_template('other.html')  # Replace with your template file name

t = {
    "test_name": "tests.BasicUbuntu.test_snap_preseed_optimized",
    "cases": [{"link": "blorp", "name": "hello moto"}]
}

j = {
    "suite": "Jammy",
    "family": "Base",
    "build_state": SUCCESS,
    "upload_state": SUCCESS,
    "test_state": WARNING,
    "pass_count": 5,
    "warn_count": 4,
    "fail_count": 0,
    "tests": [t,t,t]
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

import pre_html

context = pre_html.html_report


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


render_template_to_file('other.html', context, 'index.html')