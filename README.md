
## 🚀 Deployment (Oracle Linux / RHEL)

To deploy this application on an Oracle Linux VM (or any RHEL-based system):

1.  **Copy the deployment script** or clone the repository to your VM.
2.  **Make the script executable:**
    ```bash
    chmod +x deployment/deploy.sh
    ```
3.  **Run the script:**
    ```bash
    ./deployment/deploy.sh
    ```
    This script will automatically:
    *   Update system packages.
    *   Install Git, Docker, and Docker Compose.
    *   Clone the repository.
    *   Set up the environment.
    *   Start the application using `docker-compose.prod.yml`.

4.  **Access the API:**
    *   API: `http://<your-vm-ip>:8000`
    *   Nginx Proxy (if configured): `http://<your-vm-ip>`
