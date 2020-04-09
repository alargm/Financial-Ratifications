
# -*- coding:utf-8 -*-
from odoo import models, fields, api
from datetime import date, datetime


class RatificationListReport(models.AbstractModel):
	_name = 'report.kamil_accounting_financial_ratification.list_template'


	@api.model
	def _get_report_values(self, docids, data=None):
		
		list_type = data['form']['list_type']
		list_id = data['form']['list_id']
		for_bank_or_cash = data['form']['for_bank_or_cash']


		create_uid = False
		docs = []
		payment_number = False
		cheque_number = False
		payment_date = False
		total_net_amount_in_words = False
		description = ''

		x_create_user_id = False

		if list_type == 'ratification_list':

			for rat_list in self.env['ratification.list'].search([('id','=',list_id)]):

				description = rat_list.name
				create_uid = rat_list.create_uid.name
				x_create_user_id = rat_list.x_create_user_id.name

				total_net_amount_in_words = rat_list.total_net_amount_in_words

				for payment in self.env['ratification.payment'].search([('ratification_id.ratification_list_id','=',rat_list.id)]):
					payment_number = payment.code
					cheque_number = payment.check_number
					payment_date = payment.date

				for line in rat_list.ratification_line_ids:
					found = False
					for raw in docs:
						if raw['partner_id'] == line.partner_id.id:
							found = True
							raw['amount'] = raw['amount'] + line.amount
							raw['deduction_amount'] = raw['deduction_amount'] + line.deduction_amount

							raw['net_amount'] = raw['amount'] - raw['deduction_amount']
					if not found:
						total_deductions = 0
						for deduction_line in rat_list.other_deduction_ids:
							if deduction_line.partner_id and deduction_line.tax_id:
								if deduction_line.partner_id.id == line.partner_id.id:
									total_deductions = total_deductions + deduction_line.amount 
						
						total_deductions = total_deductions + line.deduction_amount
						docs.append({
							'partner_id' : line.partner_id.id,
							'partner_name' : line.partner_id.name,
							'amount' : line.amount,
							'deduction_amount' : total_deductions,
							'account_number' : line.partner_id.account_number,
							'bank_name' : line.partner_id.bank_name,
							'bank_branch_name' :
							line.partner_id.bank_branch_name, 
							'net_amount' : line.amount - total_deductions,
							'x_create_user_id' : x_create_user_id,
							})
				if rat_list.is_complex:
					docs = []
					for line in rat_list.partners_net_ids:
							docs.append({
							'partner_id' : line.partner_id.id,
							'partner_name' : line.partner_id.name,
							'amount' : 0,
							'deduction_amount' : 0,
							'account_number' : line.partner_id.account_number,
							'bank_name' : line.partner_id.bank_name,
							'bank_branch_name' :
							line.partner_id.bank_branch_name, 
							'net_amount' : line.net_amount,
							'x_create_user_id' : x_create_user_id,
							})



		else:
			for rat_list in self.env['ratification.list'].search([('id','=',list_id)]):
				create_uid = rat_list.create_uid.name
				x_create_user_id = rat_list.x_create_user_id.name

				for line in rat_list.ratification_line_ids:
					# found = False
					# for raw in docs:
					# 	if raw['partner_id'] == line.partner_id.id:
					# 		found = True
					# 		raw['amount'] = raw['amount'] + line.amount
					# 		raw['deduction_amount'] = raw['deduction_amount'] + line.deduction_amount
					# 		raw['net_amount'] = raw['net_amount'] + line.net_amount
					# if not found:


						docs.append({
							'partner_id' : line.partner_id.id,
							'partner_name' : line.partner_id.name,
							'amount' : line.amount,
							'deduction_amount' : line.deduction_amount,
							'account_number' : line.partner_id.account_number,
							'net_amount' : line.net_amount,
							'account_name' : line.account_id.name,
							'bank_name' : line.partner_id.bank_name,
							'bank_branch_name' :
							line.partner_id.bank_branch_name, 
							'x_create_user_id' : x_create_user_id,
							})




		return {
			'doc_ids': data['ids'],
			'doc_model': data['model'],
			'docs' : docs,		
			'list_type': list_type,
			'for_bank_or_cash' : for_bank_or_cash,
			'create_uid' : create_uid,
			'x_create_user_id' : x_create_user_id,
			'payment_number' : payment_number,
			'cheque_number' : cheque_number,
			'payment_date' : payment_date,
			'total_net_amount_in_words' : total_net_amount_in_words,
			'description' : description ,
			'x_create_user_id' : x_create_user_id,
		}

