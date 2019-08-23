import logging
import src.binx_io_cfn_certificates.certificate_dns_record_provider as certificate_dns_record_provider
import src.binx_io_cfn_certificates.certificate_provider as certificate_provider
import src.binx_io_cfn_certificates.issued_certificate_provider as issued_certificate_provider
from os import getenv

logging.basicConfig(level=getenv("LOG_LEVEL", "INFO"))

logger = logging.getLogger()


def handler(request, context):
    logger.info(request)
    if request["ResourceType"] == "Custom::Certificate":
        return certificate_provider.handler(request, context)
    elif request["ResourceType"] == "Custom::IssuedCertificate":
        return issued_certificate_provider.handler(request, context)
    else:
        return certificate_dns_record_provider.handler(request, context)
