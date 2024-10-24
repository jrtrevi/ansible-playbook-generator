from flask import Flask, render_template, request, redirect, url_for, flash, send_file, after_this_request
import os
import zipfile
import yaml

app = Flask(__name__)
app.secret_key = 'some_secret_key'

# Updated roles variable
roles = [
    {"label": "Webserver", "role_command": "webserver", "tag": "web_tag"},
    {"label": "Database", "role_command": "database", "tag": "db_tag"},
    {"label": "Cache", "role_command": "cache", "tag": "cache_tag"},
    {"label": "Load Balancer", "role_command": "load_balancer", "tag": "lb_tag"}
]

os_list = [
    {"label": "Red Hat 9", "distro": "rhel9"},
    {"label": "Amazon Linux 2", "distro": "amazonlinux2"},
]

ROLES_DIR = os.path.join(os.getcwd(), 'roles')

# Function to create playbooks for the selected roles and OS
def create_playbook(selected_roles, selected_os):
    playbooks = {}
    os_playbook_name = selected_os.replace(" ", "_")  # Format OS name

    for role in selected_roles:
        # Update the role_command with the selected OS in the format {{ selected_os }}-{{ role_command }}
        role_command = f"{os_playbook_name}-{role}"

        # Generate playbook name based on OS and role
        playbook_name = f"{os_playbook_name}-{role}.yml"
        playbook_content = [{
            'hosts': 'all',
            'become': True,
            'roles': [role_command]  # Use the customized role command with OS prefix
        }]
        playbooks[playbook_name] = playbook_content
    
    return playbooks

# Function to create the ansible.cfg file with the specified tags
def create_ansible_config(selected_tags):
    config_content = f"""[defaults]
host_key_checking = False
retry_files_enabled = False
timeout = 30

[privilege_escalation]
become = True

# Add your run tags here
[tags]
RUN_TAGS = {','.join(selected_tags)}
"""
    config_file = "ansible.cfg"
    with open(config_file, 'w') as f:
        f.write(config_content)
    return config_file

# Function to package playbooks, ansible.cfg, inventory, and roles
def package_files(playbook_paths, config_file, inventory_file, selected_roles):
    zip_filename = os.path.join(os.getcwd(), 'ansible_package.zip')
    
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        zipf.write(config_file, os.path.basename(config_file))  # Add ansible.cfg
        
        for path in playbook_paths:
            zipf.write(path, os.path.basename(path))  # Add each playbook
        
        if inventory_file:
            zipf.write(inventory_file, os.path.basename(inventory_file))  # Add inventory file

        # Add the selected roles directories (if they exist)
        for role in selected_roles:
            role_dir = os.path.join(ROLES_DIR, role)
            if os.path.exists(role_dir):
                for foldername, subfolders, filenames in os.walk(role_dir):
                    for filename in filenames:
                        filepath = os.path.join(foldername, filename)
                        arcname = os.path.relpath(filepath, start=ROLES_DIR)
                        zipf.write(filepath, os.path.join('roles', arcname))
            else:
                print(f"Role directory not found: {role_dir}")  # Log missing role directory

    if os.path.exists(zip_filename):
        print(f"ZIP file created at: {zip_filename}")
    else:
        print(f"Error: ZIP file {zip_filename} not found.")

    return zip_filename

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_roles = request.form.getlist('roles')
        selected_os = request.form.get('selected_os')

        if not selected_roles or not selected_os:
            flash("Please select both roles and an OS.", "error")
            return redirect(url_for('index'))

        # Get the tags corresponding to the selected roles
        selected_tags = [role['tag'] for role in roles if role['role_command'] in selected_roles]

        # Create playbooks and ansible.cfg file based on selected roles and OS
        try:
            # Generate playbooks
            playbooks = create_playbook(selected_roles, selected_os)

            # Write playbooks to files
            playbook_paths = []
            for playbook_name, content in playbooks.items():
                playbook_path = os.path.join(os.getcwd(), playbook_name)
                with open(playbook_path, 'w') as f:
                    f.write(yaml.dump(content, default_flow_style=False))
                playbook_paths.append(playbook_path)

            # Generate ansible.cfg based on tags
            config_file = create_ansible_config(selected_tags)

            # Generate inventory file (optional, based on user input)
            inventory_input = request.form.get('inventory_input')
            inventory_file = None
            if inventory_input:
                inventory_file = 'inventory.ini'
                with open(inventory_file, 'w') as f:
                    f.write(inventory_input)

            # Package everything into a ZIP
            zip_filename = package_files(playbook_paths, config_file, inventory_file, selected_roles)

            if not os.path.exists(zip_filename):
                flash("Error generating the ZIP file.", "error")
                return redirect(url_for('index'))

            # Schedule ZIP file removal after download
            @after_this_request
            def remove_file(response):
                try:
                    if os.path.exists(zip_filename):
                        os.remove(zip_filename)
                        print(f"Removed ZIP file: {zip_filename}")
                except Exception as e:
                    print(f"Error deleting file: {e}")
                return response

            return send_file(zip_filename, as_attachment=True)
        

        except Exception as e:
            print(f"Error creating config or zip: {e}")
            flash("Error creating the configuration package.", "error")
            return redirect(url_for('index'))

    return render_template('index.html', roles=roles, os_list=os_list)
# Run the app
if __name__ == '__main__':
    app.run(debug=True)
