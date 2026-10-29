FROM alpine:3.22 AS segments
RUN apk add --no-cache curl
ARG BROUTER_COMMIT=0b3506c31eb81f67c88affa0460291ccadcb1ec9
RUN mkdir /source && curl --fail --location --retry 3 https://codeload.github.com/abrensch/brouter/tar.gz/$BROUTER_COMMIT -o /tmp/source.tar.gz \
    && tar -xzf /tmp/source.tar.gz -C /source --strip-components=1
ARG MAP_DATA_VERSION=2026-10
RUN mkdir /segments4 && echo "$MAP_DATA_VERSION" > /segments4/snapshot.txt \
    && curl --fail --location --retry 3 --max-time 300 https://brouter.de/brouter/segments4/E10_N50.rd5 -o /segments4/E10_N50.rd5 \
    && curl --fail --location --retry 3 --max-time 300 https://brouter.de/brouter/segments4/E15_N50.rd5 -o /segments4/E15_N50.rd5

FROM eclipse-temurin:17-jdk-jammy AS build
WORKDIR /source
COPY --from=segments /source/ ./
RUN chmod +x gradlew && ./gradlew --no-daemon clean build

FROM eclipse-temurin:17-jre-jammy
LABEL org.opencontainers.image.source="https://github.com/mdriverpl/perlylubuskie.pl"
LABEL org.opencontainers.image.description="BRouter with OpenStreetMap segments for western Poland, cycling and walking"
RUN groupadd --gid 1000 brouter && useradd --uid 1000 --gid brouter --home-dir /app --no-create-home brouter \
    && mkdir -p /app /segments4 /customprofiles && chown -R brouter:brouter /app /segments4 /customprofiles
WORKDIR /app
COPY --from=build /source/brouter-server/build/libs/brouter-*-all.jar /app/brouter.jar
COPY --from=build --chmod=755 /source/misc/scripts/standalone/server.sh /app/server.sh
COPY --from=build /source/misc/profiles2/ /profiles2/
COPY --from=segments --chown=1000:1000 /segments4/ /segments4/
ENV CLASSPATH=/app/brouter.jar SEGMENTSPATH=/segments4 PROFILESPATH=/profiles2 CUSTOMPROFILESPATH=/customprofiles \
    JAVA_OPTS="-Xmx512M -Xms64M -DmaxRunningTime=30 -DmemoryClass=512" MAXTHREADS=2
USER brouter
EXPOSE 17777
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=10 CMD bash -c ': > /dev/tcp/127.0.0.1/17777'
CMD ["/app/server.sh"]
