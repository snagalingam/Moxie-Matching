# Moxie Provider-MD Matching System

This project is a web application designed to match nurses with medical directors based on various factors such as location, experience, services offered, and state licensing requirements. The application is built using Streamlit and integrates with OpenAI's API for intelligent matching.

## Setup Instructions

<<<<<<< HEAD
1. Clone the Repository: Clone this repository to your local machine.
=======
1. **Clone the Repository**: Clone this repository to your local machine.
>>>>>>> d815bbb (added readme)

   ```bash
   git clone <repository-url>
   cd Moxie-Matching
   ```

<<<<<<< HEAD
2. Create a Virtual Environment: It's recommended to use a virtual environment to manage dependencies.
=======
2. **Create a Virtual Environment**: It's recommended to use a virtual environment to manage dependencies.
>>>>>>> d815bbb (added readme)

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

<<<<<<< HEAD
3. Install Dependencies: Install the required packages using pip.
=======
3. **Install Dependencies**: Install the required packages using pip.
>>>>>>> d815bbb (added readme)

   ```bash
   pip install -r requirements.txt
   ```

<<<<<<< HEAD
4. Configure Environment Variables: Create a `.streamlit/secrets.toml` file add your OpenAI API key and any other necessary environment variables.
=======
4. **Configure Environment Variables**: Create a `.env` file in the root directory and add your OpenAI API key and any other necessary environment variables.
>>>>>>> d815bbb (added readme)

   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

5. **Run the Application**: Start the Streamlit application.

   ```bash
   streamlit run main.py
   ```

6. **Access the Application**: Open your web browser and go to `http://localhost:8501` to access the application.

## Configuration

- **Streamlit Configuration**: The `.streamlit/config.toml` file contains configuration settings for the Streamlit app.
- **Secrets Management**: Use `.streamlit/secrets.toml` to manage sensitive information like API keys and database credentials.

## License

This project is licensed under the MIT License.
