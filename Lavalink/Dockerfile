FROM eclipse-temurin:21-jre-jammy
   
WORKDIR /data

RUN useradd -m lavalink

COPY Lavalink/application.yml application.yml
COPY Lavalink/Lavalink.jar Lavalink.jar

RUN chown -R lavalink:lavalink /data

USER lavalink

CMD ["java", "-Djdk.tls.client.protocols=TLSv1.2", "-jar", "Lavalink.jar"]
