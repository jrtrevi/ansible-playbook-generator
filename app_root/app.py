from flask import Flask, render_template, request, redirect, url_for, flash, send_file, after_this_request
import yaml
import os
import zipfile
import uuid  # To create unique filenames for the ZIP packages

app = Flask(__name__)
app.secret_key = 'some_secret_key'

# Path to predefined roles (assumed to be on the server)
ROLES_DIR = 'roles/'  # Directory containing predefined roles
ZIP_DIR = '/static/zips/'  # Directory to store generated ZIP files

# Predefined roles (must match folder names in the roles directory)
roles = ["webserver", "database", "load_balancer", "firewall", "cache"]

# Function to create playbook content
def create_playbook(selected_roles):
    playbook = [{
        'hosts': 'all',
        'become': True,
        'roles': selected_roles
    }]
    return yaml.dump(playbook, default_flow_style=False)

# Function to create an inventory file from user inputs
def create_inventory(inventory_data):
    inventory_content = ""
    for group, hosts in inventory_data.items():
        inventory_content += f"[{group}]\n"
        for host in hosts:
            inventory_content += f"{host}\n"
        inventory_content += "\n"
    return inventory_content.strip()

# Function to package the playbook, inventory, and roles into a zip file
def package_files(playbook_file, inventory_file, selected_roles):
    # Define the directory where the ZIP will be saved
    zips_dir = os.path.join(os.getcwd(), 'static', 'zips')
    
    # Create the directory if it doesn't exist
    if not os.path.exists(zips_dir):
        os.makedirs(zips_dir)

    # Define the full path for the zip file
    zip_filename = os.path.join(zips_dir, 'ansible_package.zip')
    
    print(f"ZIP file will be saved to: {zip_filename}")  # Debugging

    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        zipf.write(playbook_file, os.path.basename(playbook_file))
        if inventory_file:
            zipf.write(inventory_file, os.path.basename(inventory_file))
        for role in selected_roles:
            role_dir = os.path.join(ROLES_DIR, role)
            if os.path.exists(role_dir):
                for foldername, subfolders, filenames in os.walk(role_dir):
                    for filename in filenames:
                        filepath = os.path.join(foldername, filename)
                        arcname = os.path.relpath(filepath, start=ROLES_DIR)
                        zipf.write(filepath, os.path.join('roles', arcname))

    return zip_filename

# Route for the home page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_roles = request.form.getlist('roles')
        playbook_file = request.form['playbook_file'] or 'site.yml'
        create_inventory_file = 'create_inventory' in request.form

        if not selected_roles:
            flash("Please select at least one role.")
            return redirect(url_for('index'))

        # Parse inventory input from the form
        inventory_input = request.form.get('inventory_input')
        inventory_data = {}
        if inventory_input:
            lines = inventory_input.strip().split('\n')
            current_group = None
            for line in lines:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    current_group = line[1:-1]  # Group name
                    inventory_data[current_group] = []
                elif current_group:
                    inventory_data[current_group].append(line)

        # Generate playbook content
        playbook_content = create_playbook(selected_roles)

        # Save the playbook file
        playbook_path = os.path.join(os.getcwd(), playbook_file)
        with open(playbook_path, 'w') as f:
            f.write(playbook_content)

        # Handle inventory creation
        inventory_file = None
        if create_inventory_file and inventory_data:
            inventory_file = 'inventory.ini'
            inventory_content = create_inventory(inventory_data)
            with open(inventory_file, 'w') as f:
                f.write(inventory_content)

        # Package playbook, inventory, and roles into a ZIP file
        zip_file = package_files(playbook_path, inventory_file, selected_roles)
        print(f"ZIP file created at: {zip_file}")  # Debugging: Check the path
        return redirect(url_for('download_package', filename=os.path.basename(zip_file)))


        # Redirect to download the generated ZIP file
        

    return render_template('index.html', roles=roles)

# Route to download the packaged ZIP file
@app.route('/download/<filename>')
def download_package(filename):
    # Build the full path to the ZIP file in static/zips
    file_path = os.path.join(os.getcwd(), 'static', 'zips', filename)
    print(f"Looking for file at: {file_path}")  # Debugging: Ensure the correct path

    if not os.path.exists(file_path):
        flash("File not found.")
        return redirect(url_for('index'))

    # Delete the file after it is downloaded
    @after_this_request
    def remove_file(response):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
        return response

    return send_file(file_path, as_attachment=True)


@app.route('/test-download')
def test_download():
    return send_file('/static/testfile.zip', as_attachment=True)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
