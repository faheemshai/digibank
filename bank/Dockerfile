FROM tomcat:9.0.48-jdk11-adoptopenjdk-hotspot

# Expose ports
EXPOSE 8080
EXPOSE 8443

# Set environment variables from Docker Compose configuration
# Session Management
ENV SERVER_SERVLET_SESSION_TIMEOUT=5m
ENV IO_DIGISIC_MAX_SESSIONS=10000

# Logging Options
ENV LOGGING_LEVEL_IO_DIGISIC_BANK=INFO

# Digital Broker connection
ENV SPRING_ARTEMIS_MODE=native
ENV SPRING_ARTEMIS_HOST=broker
ENV SPRING_ARTEMIS_PORT=61616
ENV SPRING_ARTEMIS_USER=admin
ENV SPRING_ARTEMIS_PASSWORD=admin

# ATM Location Service Connection
ENV IO_DIGISIC_BANK_ATM_PROTOCOL=https
ENV IO_DIGISIC_BANK_ATM_HOST=bankingservices.io
ENV IO_DIGISIC_BANK_ATM_PORT=""


# Open Banking API Service
ENV IO_DIGISIC_BANK_OBP_ENABLED=true
ENV IO_DIGISIC_BANK_OBP_CONSUMER_KEY=vwfpvwfr1kngt0up2jelebzmvxrhst4vhxvw1jm3
ENV IO_DIGISIC_BANK_OBP_VERSION=v4.0.0
ENV IO_DIGISIC_BANK_OBP_PROTOCOL=https
ENV IO_DIGISIC_BANK_OBP_HOST=""
ENV IO_DIGISIC_BANK_OBP_PORT=""

# Database Configuration
ENV SPRING_DATASOURCE_PLATFORM=postgres
ENV SPRING_DATASOURCE_USERNAME=digitaluser
ENV SPRING_DATASOURCE_PASSWORD=Demo123!
ENV SPRING_DATASOURCE_URL=jdbc:postgresql://postgres:5432/digibank
ENV SPRING_JPA_PROPERTIES_HIBERNATE_DIALECT=org.hibernate.dialect.PostgreSQLDialect

# Copy application files
COPY /target/bank##2.1.0.12.war /usr/local/tomcat/webapps/
COPY /target/classes/application.properties /usr/local/tomcat/conf/digitalbank.properties
COPY /target/classes/keystore/digisic.p12 /usr/local/tomcat/conf/digisic.p12
COPY /target/classes/server.xml /usr/local/tomcat/conf/server.xml

# Health check
HEALTHCHECK CMD curl -fail http://localhost:8080/bank/api/v1/health || exit 1