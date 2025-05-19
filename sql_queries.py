# sql_queries.py

# Example SQL queries as string constants
TICKETS_QUERY = """
SELECT 
  subject,
  bird_eats_bug_email AS provider_email,
  ticket_status,
  ticket_priority,
  kick_off_date,
  license_type AS provider_license_type,
  experience_level AS provider_experience_level,
  state_medspa_premise AS provider_state,
  md_location_preference_state AS provider_md_location_preference,
  services_provided AS provider_services,
  future_services AS provider_future_services,
  additional_service_notes AS provider_additional_services
FROM analytics.dbt.hubspot_md_tickets_mart 
WHERE bird_eats_bug_email IS NOT NULL
    AND ticket_status = 'Pending (MD Matching)'
    AND subject NOT LIKE '%Match 2%'
"""

# Add more queries as needed, e.g.:
# ANOTHER_QUERY = "SELECT ... FROM ... WHERE ..." 