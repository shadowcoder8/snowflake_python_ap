
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
    
    The application is served via Nginx on **Port 80**.
    
    *   **Public URL:** `http://<YOUR_SERVER_PUBLIC_IP>/`
    *   **API Documentation:** `http://<YOUR_SERVER_PUBLIC_IP>/docs`

    > **Note:** Direct access to port 8000 is blocked for security. You must go through Nginx (Port 80).

    ### 🛡️ Firewall Setup

    If you cannot access the API, you likely need to open Port 80 in the firewall.

    **Option A: For Oracle Linux / RHEL / CentOS (using firewalld)**
    ```bash
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --permanent --add-service=https
    sudo firewall-cmd --reload
    ```
    *If `firewall-cmd` is not found, try Option B.*

    **Option B: For Ubuntu / Debian (using UFW)**
    ```bash
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw reload
    ```

    **Option C: Oracle Cloud / AWS / Azure (Cloud Console)**
    *   Go to your Cloud Console > Networking > Security Lists / Security Groups.
    *   Add an **Ingress Rule** to allow TCP traffic on **Port 80** from `0.0.0.0/0`.
