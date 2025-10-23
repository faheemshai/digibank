FROM tomcat:9.0.48-jdk11-adoptopenjdk-hotspot
EXPOSE 8080
EXPOSE 8443
ENV LOGGING_LEVEL_IO_DIGISIC_CREDIT=INFO \
    SPRING_ARTEMIS_MODE=native \
    SPRING_ARTEMIS_HOST=broker \
    SPRING_ARTEMIS_PORT=61616 \
    SPRING_ARTEMIS_USER=admin \
    SPRING_ARTEMIS_PASSWORD=admin \
    IO_DIGISIC_CREDIT_APP_PROCESS_ENABLED=true \
    IO_DIGISIC_CREDIT_APP_PROCESS_TIME=20 \
    IO_DIGISIC_PARTNER_CREDIT_APP_REQUEST=CREDIT.APP.REQUEST \
    IO_DIGISIC_PARTNER_CREDIT_APP_RESPONSE=CREDIT.APP.RESPONSE \
    SPRING_DATASOURCE_PLATFORM=postgres \
    SPRING_DATASOURCE_USERNAME=digitaluser \
    SPRING_DATASOURCE_PASSWORD=Demo123! \
    SPRING_DATASOURCE_URL=jdbc:postgresql://postgres:5432/digicredit \
    SPRING_JPA_PROPERTIES_HIBERNATE_DIALECT=org.hibernate.dialect.PostgreSQLDialect

COPY /target/credit##2.1.0.4.war /usr/local/tomcat/webapps/
COPY /target/classes/application.properties /usr/local/tomcat/conf/digitalcredit.properties
COPY /target/classes/keystore/digisic.p12 /usr/local/tomcat/conf/digisic.p12
COPY /target/classes/server.xml /usr/local/tomcat/conf/server.xml
HEALTHCHECK CMD curl -fail http://localhost:8080/credit/api/v1/health || exit 1