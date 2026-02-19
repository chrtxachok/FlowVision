FROM rabbitmq:3.12-management-alpine

# RabbitMQ configuration
RUN rabbitmq-plugins enable --offline \
    rabbitmq_management \
    rabbitmq_prometheus

# Expose ports
EXPOSE 5672 15672 15692

# Default command
CMD ["rabbitmq-server"]
