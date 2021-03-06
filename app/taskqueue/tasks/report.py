# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""All reports related celery tasks."""

import models
import taskqueue.celery as taskc
import utils.emails
import utils.report.boot
import utils.report.build
import utils.report.common
import utils.report.error


# pylint: disable=too-many-arguments
# pylint: disable=invalid-name
# pylint: disable=too-many-locals
@taskc.app.task(name="send-boot-report", acks_late=True)
def send_boot_report(
        job,
        kernel,
        lab_name,
        email_format,
        to_addrs,
        db_options,
        mail_options,
        cc_addrs=None, bcc_addrs=None, in_reply_to=None, subject=None):
    """Create the boot report email and send it.

    :param job: The job name.
    :type job: string
    :param kernel: The kernel name.
    :type kernel: string
    :param lab_name: The name of the lab.
    :type lab_name: string
    :param email_format: The email format to send.
    :type email_format: list
    :param to_addrs: List of recipients.
    :type to_addrs: list
    :param db_options: The database connection parameters.
    :type db_options: dictionary
    :param mail_options: The options necessary to connect to the SMTP server.
    :type mail_options: dictionary
    :param cc: The list of addresses to add in CC.
    :type cc: list
    :param bcc: The list of addresses to add in BCC.
    :type bcc: list
    :param in_reply_to: The ID of the message this email is a reply to.
    :type in_reply_to: string
    :param subject: The subject string to use.
    :type subject: string.
    """
    utils.LOG.info("Preparing boot report email for '%s-%s'", job, kernel)
    status = "ERROR"

    txt_body, html_body, new_subject, headers = \
        utils.report.boot.create_boot_report(
            job,
            kernel,
            lab_name,
            email_format, db_options=db_options, mail_options=mail_options
        )

    if not subject:
        subject = new_subject

    if all([any([txt_body, html_body]), subject]):
        utils.LOG.info("Sending boot report email for '%s-%s'", job, kernel)
        status, errors = utils.emails.send_email(
            to_addrs,
            subject,
            txt_body,
            html_body,
            mail_options,
            headers=headers,
            cc_addrs=cc_addrs, bcc_addrs=bcc_addrs, in_reply_to=in_reply_to
        )
        utils.report.common.save_report(
            job, kernel, models.BOOT_REPORT, status, errors, db_options)
    else:
        utils.LOG.error(
            "No email body nor subject found for boot report '%s-%s'",
            job, kernel)

    return status


@taskc.app.task(name="send-build-report", acks_late=True)
def send_build_report(
        job,
        kernel,
        email_format,
        to_addrs,
        db_options,
        mail_options,
        cc_addrs=None, bcc_addrs=None, in_reply_to=None, subject=None):
    """Create the build report email and send it.

    :param job: The job name.
    :type job: string
    :param kernel: The kernel name.
    :type kernel: string
    :param email_format: The email format to send.
    :type email_format: list
    :param to_addrs: List of recipients.
    :type to_addrs: list
    :param db_options: The database connection parameters.
    :type db_options: dictionary
    :param mail_options: The options necessary to connect to the SMTP server.
    :type mail_options: dictionary
    :param cc: The list of addresses to add in CC.
    :type cc: list
    :param bcc: The list of addresses to add in BCC.
    :type bcc: list
    :param in_reply_to: The ID of the message this email is a reply to.
    :type in_reply_to: string
    :param subject: The subject string to use.
    :type subject: string
    """
    utils.LOG.info("Preparing build report email for '%s-%s'", job, kernel)
    status = "ERROR"

    txt_body, html_body, new_subject, headers = \
        utils.report.build.create_build_report(
            job,
            kernel,
            email_format,
            db_options=db_options,
            mail_options=mail_options
        )

    if not subject:
        subject = new_subject

    if all([any([txt_body, html_body]), subject]):
        utils.LOG.info("Sending build report email for '%s-%s'", job, kernel)
        status, errors = utils.emails.send_email(
            to_addrs,
            subject,
            txt_body,
            html_body,
            mail_options,
            headers=headers,
            cc_addrs=cc_addrs, bcc_addrs=bcc_addrs, in_reply_to=in_reply_to
        )
        utils.report.common.save_report(
            job, kernel, models.BUILD_REPORT, status, errors, db_options)
    else:
        utils.LOG.error(
            "No email body nor subject found for build report '%s-%s'",
            job, kernel)

    return status


@taskc.app.task(name="send-multi-email-errors-report")
def send_multiple_emails_error(job, kernel, date, email_format, data):
    to_addrs = []
    cc_addrs = []

    email_data = {
        "job": job,
        "kernel": kernel,
        "trigger_time": date,
        "email_format": email_format,
        "to_addrs": to_addrs,
        "cc_addrs": cc_addrs,
        "subject": data.get("subject"),
        "in_reply_to": data.get("in_reply_to"),
        "trigger_time": date
    }

    if data.get("generic_emails"):
        to_addrs.extend(data.get("generic_emails"))
    if data.get("boot_emails"):
        to_addrs.extend(data.get("boot_emails"))
    if data.get("build_emails"):
        to_addrs.extend(data.get("build_emails"))

    if data.get("build_cc_emails"):
        cc_addrs.extend(data.get("build_cc_emails"))
    if data.get("build_bcc_emails"):
        cc_addrs.extend(data.get("build_cc_emails"))
    if data.get("boot_cc_emails"):
        cc_addrs.extend(data.get("boot_cc_emails"))
    if data.get("boot_bcc_emails"):
        cc_addrs.extend(data.get("boot_bcc_emails"))
    if data.get("generic_cc_emails"):
        cc_addrs.extend(data.get("generic_cc_emails"))
    if data.get("generic_bcc_emails"):
        cc_addrs.extend(data.get("generic_bcc_emails"))

    txt_body, html_body, subject = \
        utils.report.error.create_duplicate_email_report(email_data)

    if all([any([txt_body, html_body]), subject]):
        utils.LOG.info(
            "Sending duplicate emails report for %s - %s", job, kernel)
        utils.emails.send_email(
            [taskc.app.conf.mail_options.get("error_email")],
            subject,
            txt_body,
            html_body,
            taskc.app.conf.mail_options
        )
