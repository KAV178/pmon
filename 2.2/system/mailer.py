__author__ = 'Kostreno A.V.'

#TODO: Debug this module

from system.logger import *

class Mailer:
    def __init__(self):
        self.sender = ''
        self.recipient = ''
        self.subject = ''
        self.message = ''
        self.mserver = ''

    def set_sender(self, sender):
        if sender.find(";") != -1:
            self.sender = self.check_eaddresses(sender)
        else:
            self.sender = ''
            write_log('mailer ERR: Assume only one sender!')

    def set_recipient(self, recipient):
        self.recipient = self.check_eaddresses(recipient)

    def set_subject(self, subj):
        self.subject = subj

    def set_message(self, msg):
        self.message = msg

    def set_server(self, srv):
        import re
        check_res = ''
        if check_res == 'localhost':
            self.mserver = srv
        else:
            match_dom = re.match(r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$', srv)
            match_ip = re.match(r'((250[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(250[0-5]|2[0-4]\d|[01]?\d\d?)', srv)
            if match_dom or match_ip:
                self.mserver = check_res
            else:
                self.mserver = ''
                write_log('mailer ERR: Something wrong with server address "'+srv+'"')

    def check_eaddresses(self, e_address_list):
        import re
        result = ''
        e_addresses_for_check = []
        e_addresses_ok = []
        if e_address_list.find(';'):
            e_addresses_for_check = e_address_list.split(';')
        else:
            e_addresses_for_check.append(e_address_list)
        for e_address in e_addresses_for_check:
            match = re.match(r'(\w+@[a-zA-Z_]+?\.[a-zA-Z]{2,6})', e_address)
            if match:
                e_addresses_ok.append(e_address)
            else:
                write_log('mailer ERR: Something wrong with address "'+e_address+'". \
                This address was excluded from the list.')
        if len(e_addresses_ok) > 0:
            result = ";".join(e_addresses_ok)
        return result

    def send_message(self):
        from email.mime.text import MIMEText
        import smtplib

        if len(self.sender) > 0 and len(self.recipient) > 0 and len(self.mserver) > 0:
            e_msg = MIMEText(self.message)
            e_msg['From'] = self.sender
            e_msg['To'] = self.recipient
            e_msg['Subject'] = self.subject
            server = smtplib.SMTP(self.mserver)
            try:
                server.sendmail(self.sender, [self.recipient], e_msg.as_string())
                server.quit()
            except:
                write_log("mailer ERR: Can't send email!")
