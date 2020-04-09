from odoo import models,fields,api,_ 
from odoo.exceptions import ValidationError
from . import amount_to_text as amount_to_text_ar
from dateutil.relativedelta import relativedelta


class Ratification(models.Model):
	_name = 'ratification.ratification'
	_description = 'Ratification'
	_order = 'id desc'
	_rec_name = 'the_name'
	_inherit = ['mail.thread','mail.activity.mixin', 'portal.mixin']

	the_name = fields.Char(compute='get_the_name')

	ref = fields.Char(string="Ratification Number",track_visibility='always',copy=False, default='/')
	partner_id = fields.Many2one('res.partner', string='Payee',track_visibility='always')
	state_id = fields.Many2one('res.company', string='Branch',default= lambda self:self.env.user.company_id.id,track_visibility='always')
	date = fields.Date(string='Date',default=fields.date.today(),track_visibility='always')
	
	ratification_list_id = fields.Many2one('ratification.list',string='Ratification List')

	ratification_type = fields.Selection([('salaries_and_benefits','Salaries and Benefits'),('prepaid_expenses', 'Prepaid Expenses'),('service_provider_claim','Service Provider Claim'),('service_provider_loan','Service Provider Loan'),('purchases_and_inventory','Purchases and Inventory'),('petty_cash','Petty Cash'),('petty_cash','Permanent Petty Cash'),('employee_loan','Employee Loan'),('other','Other')],default='other',track_visibility='always')
	payment_type = fields.Selection([('Cheque','Cheque'),('cash','Cash'),('bank_transfer','Bank Transfer'),('counter_cheque','Counter Cheque')], default='Cheque',track_visibility='always')

	source_id = fields.Char()

	name = fields.Text(string='Description',track_visibility='always')

	currency_id = fields.Many2one('res.currency', string='Currency' ,default= lambda self:self.env.user.company_id.currency_id.id)

	amount = fields.Float(compute='compute_amount', track_visibility='always')
	amount_in_words = fields.Char(compute='get_total_in_words' ,track_visibility='always')


	state = fields.Selection([('draft','Draft'),('executed','Under Execution'),('audited','Approved'),('payment_created','Payment Created'),('payment_confirmed','Payment Confirmed'),('paid','Paid'),('canceled','Canceled')], default='draft',track_visibility='always')

	line_ids = fields.One2many('ratification.line', 'ratification_id', copy=True)
	tax_ids = fields.One2many('ratification.tax.line', 'ratification_id', copy=True)
	loan_ids = fields.One2many('ratification.loan.line', 'ratification_id', copy=True)
	

	service_provider_loan_amount = fields.Float(string='Loan Amount',track_visibility='always')
	
	number_of_installment = fields.Integer(string='Number of Installments',track_visibility='always')
	

	service_provider_loan_payment_term = fields.Selection([(1,'Monthly'),(3,'Quarterly'),(6,'Biannual'),(12,'Annual')])
	
	service_provider_loan_start_date = fields.Date(default=fields.Date.today())

	installment_ids = fields.One2many('ratification.installment', 'ratification_id', copy=True)

	prepaid_expenses_number_of_installment = fields.Integer(string='Number of Installments',track_visibility='always')
	
	prepaid_expenses_payment_term = fields.Selection([(1,'Monthly'),(3,'Quarterly'),(6,'Biannual'),(12,'Annual')])
	
	prepaid_expenses_start_date = fields.Date(default=fields.Date.today())

	prepaid_expenses_amount = fields.Float()
	
	prepaid_expenses_account_id = fields.Many2one('account.account', string='Transfer to Account', domain=[('is_group','=','sub_account')])
	prepaid_expenses_budget_item_id = fields.Many2one('account.analytic.account', string='Budget Item')

	prepaid_expenses_installment_ids = fields.One2many('ratification.prepaid.expenses', 'ratification_id', copy=True)

	total_taxes_amount = fields.Float(compute='compute_tax_ids',track_visibility='always')
	total_taxes_amount_in_words = fields.Char(compute='compute_tax_ids',track_visibility='always',string='Taxes Amount in Words')

	total_loan_amount = fields.Float(compute='compute_loans_ids',track_visibility='always')
	total_loan_amount_in_words = fields.Char(compute='compute_loans_ids',track_visibility='always',string='Loans Amount in Words')

	net_amount = fields.Float(compute='compute_net_amount',track_visibility='always')
	net_amount_in_words = fields.Char(compute='compute_net_amount',track_visibility='always')

	petty_cash_amount = fields.Float()

	has_loan = fields.Boolean()

	has_prepaid = fields.Boolean(default=False, compute='get_ratification_values')

	line_has_loan = fields.Boolean(default=False, compute='get_ratification_values' )

	has_petty_cash = fields.Boolean(default=False, compute='get_ratification_values' )

	partner_is_bank = fields.Boolean()

	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)

	report_line_ids = fields.Many2many('ratification.report.line')

	financial_year = fields.Char(compute='get_financial_year')
	for_items = fields.Char(compute='get_for_items')
	x_create_user_id = fields.Many2one('res.users', string='Created by', default= lambda self:self.env.user.id)
	

	@api.multi
	def get_for_items(self):
		for record in  self:

			ids_list = []
			for line in record.line_ids:
				if line.account_id.code[:2] not in ids_list:
					ids_list.append( line.account_id.code[:2] )

			record.for_items = ''
			for account in self.env['account.account'].search([('code','in',ids_list)]):
				record.for_items = record.for_items + ',' + account.name



			# if len(record.line_ids) == 1:
			# 	for line in record.line_ids:
			# 		if line.analytic_account_id:
			# 			record.for_items = line.analytic_account_id.name

			# 		else:
			# 			record.for_items = line.account_id.name

			# if len(record.line_ids) > 1:
			# 	record.for_items = 'بنود متعددة'



	@api.multi
	def get_financial_year(self):
		for record in self:
			if record.date:
				record.financial_year = record.date.year


	@api.multi
	def unlink(self):
		for record in self:
			if record.state not in ['draft','canceled']:
				raise ValidationError(_('You Can not delete a Record, witch is not Draft or Canceled'))

			if record.ratification_list_id:
				if len(record.line_ids._ids) == 1:
					for line in record.line_ids:
						line.ratification_id = False
				else:
					self._cr.execute("UPDATE ratification_line set ratification_id = null where ratification_id=" + str(record.id) + " " )
			return super(Ratification, self).unlink()


	@api.multi
	@api.onchange('ratification_list_id')
	def onchange_ratification_list_id(self):
		for record in self:
			if record.ratification_list_id:
				record.line_ids = False
				record.tax_ids = False

				for line in record.ratification_list_id.ratification_line_ids:
					line.ratification_id = record.id
#############################################################

				report_line_list = []
				account_ids = []
				for line in record.ratification_list_id.other_deduction_ids:

					if line.tax_id.account_id and line.partner_id:
						if line.tax_id.account_id.id not in account_ids:
							
							account_ids.append( line.tax_id.account_id.id )
							report_line_list.append( {'name' : line.tax_id.account_id.name, 'amount' : line.amount, 'account_id' : line.tax_id.account_id.id, 'partner_id':line.partner_id.id, 'tax_id': line.tax_id.id} )
						else:
							for row in report_line_list:
								if row['account_id'] == line.tax_id.account_id.id:
									row['amount'] = row['amount'] + line.amount

				for row in report_line_list:
					record.tax_ids = [(0,0,{
						'name' : row['name'],
						'account_id' : row['account_id'],
						'amount' : row['amount'],
						'partner_id' : row['partner_id'],
						'tax_id' : row['tax_id'],
						})]





#############################################################
				# for tax_line in record.ratification_list_id.other_deduction_ids:
				# 	if tax_line.partner_id and tax_line.tax_id.id:
				# 		record.tax_ids = [(0,0,{
				# 			'partner_id' :  tax_line.partner_id,
				# 			'name' : tax_line.name,
				# 			'tax_id' : tax_line.tax_id.id,
				# 			'amount' : tax_line.amount,
				# 			})]
				record.name = record.ratification_list_id.name
				record.the_name = record.ratification_list_id.name




			# record.tax_ids = False
			# if record.ratification_list_id:
				
			# 	taxes_list = []

			# 	for tax in record.ratification_list_id.tax_amount_ids:
					
			# 		if tax.tax_id.id not in taxes_list:
			# 			taxes_list.append( tax.tax_id.id )

			# 	for tax_id in taxes_list:
			# 		amount = 0
			# 		tax_name = ''
			# 		for tax in record.ratification_list_id.tax_amount_ids:
			# 			if tax.tax_id.id == tax_id:
			# 				amount = amount + tax.amount
			# 				tax_name = tax.tax_id.name
			# 		record.tax_ids = [(0,0,{
			# 			'name' : tax_name,
			# 			'tax_id' : tax_id,
			# 			'amount' : amount,
			# 			})]	


			# 	record.line_ids = False
			# 	for ratification_list_line in record.ratification_list_id.line_ids:

			# 		record.line_ids = [(0,0,{
			# 			'partner_id' : ratification_list_line.partner_id,
			# 			'name' : ratification_list_line.name,
			# 			'analytic_account_id' : ratification_list_line.analytic_account_id.id,
			# 			'account_id' : ratification_list_line.account_id.id,
			# 			'cost_center_id' : ratification_list_line.cost_center_id.id,
			# 			'amount' : ratification_list_line.amount,
			# 			'analytic_tag_ids' : [(6,0, ratification_list_line.analytic_tag_ids._ids )],
			# 			'ratification_type' : ratification_list_line.ratification_type,
			# 			'branch_id' : self.env.user.company_id.id,
			# 			})]




	@api.multi
	def compute_taxs(self):
		for record in self:		
			record.tax_ids = False
			for line in record.line_ids:
				for tax_line in line.deduction_ids:
					
					tax_found = False
					for record_tax in record.tax_ids:
						if record_tax.tax_id == tax_line.tax_id:
							record_tax.amount = record_tax.amount + tax_line.amount
							tax_found = True
					if not tax_found:
						record.tax_ids = [(0,0,{
							'tax_id' : tax_line.tax_id.id,
							'amount' : tax_line.amount,
							'name' : tax_line.tax_id.name,
							})]


			if record.ratification_list_id:

				report_line_list = []
				account_ids = []
				for line in record.ratification_list_id.other_deduction_ids:

					if line.tax_id.account_id and line.partner_id:
						if line.tax_id.account_id.id not in account_ids:
							
							account_ids.append( line.tax_id.account_id.id )
							report_line_list.append( {'name' : line.tax_id.account_id.name, 'amount' : line.amount, 'account_id' : line.tax_id.account_id.id, 'partner_id':line.partner_id.id ,'tax_id': line.tax_id.id} )
						else:
							for row in report_line_list:
								if row['account_id'] == line.tax_id.account_id.id:
									row['amount'] = row['amount'] + line.amount

				for row in report_line_list:
					record.tax_ids = [(0,0,{
						'name' : row['name'],
						'account_id' : row['account_id'],
						'amount' : row['amount'],
						'partner_id' : row['partner_id'],
						'tax_id' : row['tax_id'],
						})]


			# if record.ratification_list_id:
			# 	for tax_line in record.ratification_list_id.other_deduction_ids:
			# 		record.tax_ids = [(0,0,{
			# 			'partner_id' :  tax_line.partner_id,
			# 			'name' : tax_line.name,
			# 			'tax_id' : tax_line.tax_id.id,
			# 			'amount' : tax_line.amount,
			# 			})]


	@api.multi
	@api.depends('line_ids')
	def get_ratification_values(self):
		for record in self:
			record.name  = ''
			record.has_prepaid = False
			record.line_has_loan = False
			record.has_petty_cash = False

			record.prepaid_expenses_amount = 0
			record.service_provider_loan_amount = 0
			record.petty_cash_amount = 0

			self.compute_taxs()

			for line in record.line_ids:
				if line.ratification_type == 'prepaid_expenses':
					record.has_prepaid = True
					record.prepaid_expenses_amount = record.prepaid_expenses_amount + line.amount

				if line.ratification_type == 'service_provider_loan':
					record.line_has_loan = True
					record.service_provider_loan_amount = record.service_provider_loan_amount + line.amount

				if line.ratification_type == 'petty_cash':
					record.has_petty_cash = True
					record.petty_cash_amount = record.petty_cash_amount + line.amount

				# total_name = record.name or ''
				# line_name = line.name or ''

				# record.name = total_name + '\n' + line_name + ' + '


	@api.multi
	def show_payments(self):

		for payment in self.env['ratification.payment'].search([('ratification_id','=',self.id)]):
			
			return {
				'type' : 'ir.actions.act_window',
				'view_mode' : 'form',
				'res_model' : 'ratification.payment',
				'res_id' : payment.id,
				'domain' : [('ratification_id','=', self.id )],
				'context' : {'default_ratification_id':self.id}, 
			}			

		return {
			'type' : 'ir.actions.act_window',
			'view_mode' : 'form',
			'res_model' : 'ratification.payment',
			'domain' : [('ratification_id','=', self.id )],
			'context' : {'default_ratification_id':self.id}, 
		}



	def show_prepaid_expenses_installments(self):
		return {
			'type' : 'ir.actions.act_window',
			'view_mode' : 'tree,form',
			'res_model' : 'ratification.prepaid.expenses',
			'domain' : [('ratification_id','=', self.id )],
			'context' : {'default_ratification_id':self.id}, 
		}


	def show_service_provider_loan_installments(self):
		return {
			'type' : 'ir.actions.act_window',
			'view_mode' : 'tree,form',
			'res_model' : 'ratification.installment',
			'domain' : [('ratification_id','=', self.id )],
			'context' : {'default_ratification_id':self.id}, 
		}


	def show_clearance(self):
		return {
			'type' : 'ir.actions.act_window',
			'view_mode' : 'tree,form',
			'res_model' : 'ratification.petty.cash.clearance',
			'domain' : [('ratification_id','=', self.id )],
			'context' : {'default_ratification_id':self.id}, 
		}


	@api.multi
	def do_cancel(self):
		for record in self:
			if record.state == 'audited':
				for line in record.line_ids:
					if line.analytic_account_id:
						self.env['crossovered.budget'].budget_operations(do_just_check=False, do_reserve=False, do_actual=True, budget_item=line.analytic_account_id, account=line.account_id,amount=line.amount,date=record.date)
			record.state = 'canceled'



	@api.multi
	def do_reset_to_draft(self):
		self.state = 'draft'


	@api.multi
	def do_confirm(self):
		for record in self:

			if len(record.line_ids) < 1:
				raise ValidationError(_('Please Add Details!'))
			
			if record.line_has_loan:
				if len(record.installment_ids) <= 0:
					raise ValidationError(_('Please Add Installments Details'))
			for line in record.line_ids:
				if line.amount <= 0:
					raise ValidationError(_( 'please add a valide number for the Account ' +  line.account_id.name ))

			# if record.ratification_list_id:
			# 	list_amount = 0
			# 	deduc_amount = 0
			# 	for list_line in record.ratification_list_id.line_ids:
			# 		list_amount = list_amount + list_line.amount
			# 		deduc_amount = deduc_amount + list_line.deduction_amount

			# 	if record.amount != list_amount :
			# 		raise ValidationError(_('Sorry!, the amount in the ratification should be equal to the amount in the ratification list'))

			# 	if record.total_taxes_amount != deduc_amount :
			# 		raise ValidationError(_('Sorry!, the deductions amount in the ratification should be equal to the deductions amount in the ratification list'))



			if record.has_prepaid:
				if len(record.prepaid_expenses_installment_ids) <= 0:
					raise ValidationError(_('Please Add Prepaid Expenses Installments Details'))

			for line in record.line_ids:
				if line.analytic_account_id:
					self.env['crossovered.budget'].budget_operations(do_just_check=True, do_reserve=False, do_actual=False, budget_item=line.analytic_account_id, account=line.account_id,amount=line.amount, date=record.date)
				



			report_line_list = []
			account_ids = []
			for line in record.line_ids:
				if line.account_id.id not in account_ids:
					account_ids.append( line.account_id.id )
					report_line_list.append( {'name' : line.account_id.name, 'amount' : line.amount, 'account_id' : line.account_id.id , 'analytic_account_id':line.analytic_account_id.id } )

				else:
					for row in report_line_list:
						if row['account_id'] == line.account_id.id:
							row['amount'] = row['amount'] + line.amount

			record.report_line_ids = False
			for row in report_line_list:
				record.report_line_ids = [(0,0,{
					'account_id' : row['account_id'],
					'amount' : row['amount'],
					'analytic_account_id' : row['analytic_account_id'],
					})]

			self._cr.execute("UPDATE ratification_ratification SET create_uid = " + str(self.env.user.id) + " WHERE id = " + str(self.id) )
			
			record.state = 'executed'
			

	@api.multi
	def do_audit(self):
		for record in self:
		
			# for line in record.line_ids:
			# 	if line.analytic_account_id:
			# 		self.env['crossovered.budget'].budget_operations(do_just_check=False, do_reserve=True, do_actual=False, budget_item=line.analytic_account_id, account=line.account_id,amount=line.amount, date=record.date)
			record.state = 'audited'

			if record.has_prepaid:
				for line in record.prepaid_expenses_installment_ids:
					self.env['mail.activity'].create({
						'res_name': _('Prepaid Expenses Installment'),
						'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
						'note': _('Do the Transfer Operation'),
						'date_deadline': line.due_date,
						'summary': _('Do the Transfer Operation'),
						'user_id': self.env.user.id,
						'res_id': line.id,
						'res_model_id': self.env.ref('kamil_accounting_financial_ratification.model_ratification_prepaid_expenses').id,
					})
			

	@api.multi
	@api.depends('ref','name')
	def get_the_name(self):
		for record in self:
			record.the_name = record.ref + ' - ' + record.name

	@api.multi
	@api.depends('tax_ids')
	def compute_tax_ids(self):
		for record in self:
			total = 0
			for tax_line in record.tax_ids:
				total = total + tax_line.amount
			record.total_taxes_amount = total
			record.total_taxes_amount_in_words = amount_to_text_ar.amount_to_text(total, 'ar')



	@api.multi
	@api.depends('loan_ids')
	def compute_loans_ids(self):
		for record in self:
			total_loans = 0			
			for loan_line in record.loan_ids:
				if record.has_loan:
					if loan_line.is_add_loan:
						total_loans = total_loans + loan_line.added_amount
			record.total_loan_amount = total_loans
			record.total_loan_amount_in_words = amount_to_text_ar.amount_to_text(total_loans, 'ar')


	@api.multi
	@api.depends('line_ids','loan_ids','tax_ids')
	def compute_net_amount(self):
		for record in self:
			total = 0
			total_taxes = 0
			total_loans = 0
			
			for total_line in record.line_ids:
				total = total + total_line.amount
			for tax_line in record.tax_ids:
				total_taxes = total_taxes + tax_line.amount
			for loan_line in record.loan_ids:
				if record.has_loan:
					if loan_line.is_add_loan:
						total_loans = total_loans + loan_line.added_amount

			net = total - total_taxes - total_loans
			record.net_amount = net
			record.net_amount_in_words = amount_to_text_ar.amount_to_text(net, 'ar')



	@api.multi
	@api.onchange('partner_id')
	def onchange_partner(self):
		found_ones = False
		for record in self:
			if record.partner_id:
				record.loan_ids = False
				for ratification in self.env['ratification.ratification'].search([('partner_id','=', record.partner_id.id),('state','!=','draft'),('ratification_type','=','service_provider_loan')]):
					
					for installment in ratification.installment_ids:
						if not installment.is_paid:
							found_ones = True
							record.loan_ids = [(0,0,{
								'name' : installment.name,
								'loan_date' : installment.date,
								'loan_amount' : installment.amount,
								})]
					if found_ones:
						record.has_loan = True

			if not found_ones:
				record.has_loan = False
				record.loan_ids = False
			else:
				self.env.user.notify_danger(message=_( record.partner_id.name + ' Has Loans'))

			if record.partner_id.is_bank == 'cashier':
				record.partner_is_bank = True
			else:
				record.partner_is_bank = False

			

	@api.multi
	@api.depends('line_ids')
	def compute_amount(self):
		for record in self:
			total = 0
			for line in record.line_ids:
				total = total + line.amount
			record.amount = total


	@api.multi
	def get_amount_in_words(self, amount=0.0):
		for record in self:
			record.amount_in_words  = amount_to_text_ar.amount_to_text(amount, 'ar')

	@api.multi
	@api.depends('line_ids')
	def get_total_in_words(self):
		for record in self:
			record.amount_in_words = amount_to_text_ar.amount_to_text( record.amount )


	@api.model 
	def create(self, vals):
		# vals['ref'] = self.env['ir.sequence'].next_by_code('ratification.sequence') or '/'
		vals['name'] = self.env["ir.fields.converter"].text_from_html(vals['name'], 40, 1000, "...")
		vals['x_create_user_id'] = self.env.user.id

		create_id = super(Ratification, self).create(vals)

		# taxs_total = 0
		# for tax_line in create_id.tax_ids:
		# 	taxs_total = taxs_total + tax_line.amount
		# if taxs_total >= 0:
			# self.env.user.notify_danger(message=_("There is no Taxes!!") )
		if create_id.date:
			seq_code = 'ratification.sequence.' + str(create_id.date.year) + '.' + str(create_id.date.month)
			seq = self.env['ir.sequence'].next_by_code( seq_code )
			if not seq:
				self.env['ir.sequence'].create({
					'name' : seq_code,
					'code' : seq_code,
					'prefix' :  str(create_id.date.year) + '-' +  str(create_id.date.month) + '-' ,
					'number_next' : 1,
					'number_increment' : 1,
					'use_date_range' : True,
					'padding' : 4,
					})
				seq = self.env['ir.sequence'].next_by_code( seq_code )
			create_id.ref = seq 

		return create_id

	@api.multi 
	def write(self, vals):
		if vals.get('name', False):
			vals['name'] = self.env["ir.fields.converter"].text_from_html(vals['name'], 40, 1000, "...")
		# return super(Ratification, self).write(vals)
		vals['x_create_user_id'] = self.env.user.id 
		write_id = super(Ratification, self).write(vals)
		if vals.get('date', False):
			seq_code = 'ratification.sequence.' + str(self.date.year) + '.' + str(self.date.month)
			seq = self.env['ir.sequence'].next_by_code( seq_code )
			if not seq:
				self.env['ir.sequence'].create({
					'name' : seq_code,
					'code' : seq_code,
					'prefix' :  str(self.date.year) + '-' +  str(self.date.month) + '-' ,
					'number_next' : 1,
					'number_increment' : 1,
					'use_date_range' : True,
					'padding' : 4,
					})
				seq = self.env['ir.sequence'].next_by_code( seq_code )
			self.ref = seq 

		return write_id



	@api.multi
	@api.onchange('service_provider_loan_amount','number_of_installment','service_provider_loan_payment_term','service_provider_loan_start_date')
	def calculate_installments(self):
		for record in self:
			if record.number_of_installment > 0 and record.service_provider_loan_amount > 0 and record.service_provider_loan_payment_term and record.service_provider_loan_start_date:

				loan_account = False
				# if record.line_ids:
				# 	if record.line_ids[0]:
				# 		loan_account = record.line_ids[0].account_id

				for line in record.line_ids:
					loan_account = line.account_id

				installment_amount = record.service_provider_loan_amount / record.number_of_installment

				record.installment_ids = False
				for i in range( record.number_of_installment ):
					record.installment_ids = [(0,0,{
						'amount' : installment_amount,
						'date' : record.service_provider_loan_start_date + relativedelta(months=+ (i * int(record.service_provider_loan_payment_term))  ) ,
						'name' : '-------------',
						'account_id' : loan_account.id,
						})]


	@api.multi
	@api.onchange('prepaid_expenses_number_of_installment','prepaid_expenses_payment_term','prepaid_expenses_start_date','prepaid_expenses_amount')
	def calculate_prepaid_expenses_installments(self):
		for record in self:
			if record.prepaid_expenses_number_of_installment > 0 and record.prepaid_expenses_amount > 0:

				prepaid_account = False
				prepaid_amount = 0
				for line in record.line_ids:
					if line.ratification_type == 'prepaid_expenses':
						prepaid_account = line.account_id
						prepaid_amount = line.amount						

				installment_amount = record.prepaid_expenses_amount / record.prepaid_expenses_number_of_installment

				record.prepaid_expenses_installment_ids = False
				
				for i in range( record.prepaid_expenses_number_of_installment ):
					record.prepaid_expenses_installment_ids = [(0,0,{
						'amount' : installment_amount,
						'date' : record.date,
						'due_date' : record.prepaid_expenses_start_date + relativedelta(months=+ (i * int(record.prepaid_expenses_payment_term))  ) ,
						'name' : '-------------',
						'account_id' : prepaid_account.id,
						})]



	@api.multi
	@api.onchange('prepaid_expenses_account_id','prepaid_expenses_budget_item_id')
	def onchange_account_budget_item(self):
		for record in self:
			
			if record.prepaid_expenses_account_id:
				for line in record.prepaid_expenses_installment_ids:
					line.to_account_id = record.	prepaid_expenses_account_id
			else:
				for line in record.prepaid_expenses_installment_ids:
					line.to_account_id = False

			if record.prepaid_expenses_budget_item_id:
				for line in record.prepaid_expenses_installment_ids:
					line.analytic_account_id = record.prepaid_expenses_budget_item_id
			else:
				for line in record.prepaid_expenses_installment_ids:
					line.analytic_account_id = False

				



	@api.multi
	@api.onchange('service_provider_loan_amount')
	def onchange_loan_amount(self):
		for record in self:
			if record.service_provider_loan_amount > record.amount:
				raise ValidationError(_('Loan Amount can not be bigger than total amount'))


	@api.multi
	@api.onchange('prepaid_expenses_account_id')
	def onchange_prepaid_expenses_account(self):
		for record in self:
			if record.prepaid_expenses_account_id:
				record.prepaid_expenses_budget_item_id = record.prepaid_expenses_account_id.parent_budget_item_id


class RatificationLine(models.Model):
	_name = 'ratification.line'

	partner_id = fields.Many2one('res.partner')
	name = fields.Char(string='Description')
	analytic_account_id = fields.Many2one('account.analytic.account',string='Budget Item')
	account_id = fields.Many2one('account.account', string='Account')
	cost_center_id = fields.Many2one('kamil.account.cost.center', string='Cost Center')
	analytic_tag_ids = fields.Many2many('account.analytic.tag',string='Analytic Tags')
	amount = fields.Float()
	ratification_id = fields.Many2one('ratification.ratification', ondelete='cascade')
	ratification_list_id = fields.Many2one('ratification.list', ondelete='cascade')

	branch_id = fields.Many2one('res.company', string='Branch',default= lambda self:self.env.user.company_id.id)


	the_type = fields.Selection([('budget','Budget'),('accounts_receivable','Accounts Receivable'),('accounts_payable','Accounts Payable')], default='budget', string="Ratification Type")

	accounts_receivable_types = fields.Selection([
		('accounts_receivable','Accounts Receivable'),
		('petty_cash','Petty Cash'),
		('service_provider_loan','Service Provider Loans'),
		('prepaid_expenses', 'Prepaid Expenses')], default='accounts_receivable', string='Sub Type' )

	accounts_payable_types = fields.Selection([
		('accounts_payable','Accounts Payable'),
		('service_provider_claim','Service Provider Claim')],default='accounts_payable', string='Sub Type')

	ratification_type = fields.Selection([
		('expenses','expenses'),
		('purchases','Purchases'),
		('accounts_receivable','Accounts Receivable'),
		('petty_cash','Petty Cash'),
		('service_provider_loan','Service Provider Loans'),
		('prepaid_expenses', 'Prepaid Expenses'),
		('accounts_payable','Accounts Payable'),
		('service_provider_claim','Service Provider Claim')],default='expenses',track_visibility='always')

	date = fields.Date(related='ratification_id.date', store=True)

	approved_value = fields.Float(compute='get_budget_amounts')
	remaining_value = fields.Float(compute='get_budget_amounts')

	service_levels = fields.Selection([('level_one','Level One'),('level_two','Level Two'),('level_three','Level Three')])
	level_id = fields.Many2one('ratification.line.level', string='Level')
	tag_ids = fields.One2many('ratification.line.tag', 'ratification_line_id', copy=True)
	state = fields.Selection(related='ratification_id.state', store=True)

	deduction_ids = fields.One2many('ratification.line.tax.line','ratification_line_id', string='Deductions', copy=True)
	deduction_amount = fields.Float(compute='get_net_amount')
	net_amount = fields.Float(compute='get_net_amount')
	account_code = fields.Char()
	item_type = fields.Selection([('medicine','Medicine'),('labs','Labs'),('transformed','Transformed'),('other','Other')],default='other')

	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)



	@api.multi
	@api.onchange('deduction_ids','amount')
	def compute_deduction_amount(self):
		for record in self:

			record.ratification_id.compute_taxs()
			
			tax_amount = 0
			for tax in record.deduction_ids:
				if tax.tax_id.amount_type == 'fixed':
					tax_amount = tax_amount + tax.tax_id.amount
				if tax.tax_id.amount_type == 'percent':
					tax_amount = tax_amount + (tax.amount * record.amount / 100)
			record.deduction_amount = tax_amount



	@api.multi
	@api.depends('amount','deduction_amount')
	def get_net_amount(self):
		for record in self:
			deduction_amount = 0
			for line in record.deduction_ids:
				deduction_amount = deduction_amount + line.amount

			record.deduction_amount = deduction_amount
			record.net_amount = record.amount - record.deduction_amount




	@api.multi
	@api.onchange('tag_ids')
	def onchange_tag_ids(self):
		for record in self:
			total = 0
			for line in record.tag_ids:
				total = total + line.amount 
			if total > record.amount:
				raise ValidationError(_('Tags amount can not be bigger than budget item amount'))



	@api.multi
	@api.onchange('amount')
	def onchange_amount(self):
		for record in self:
			if record.analytic_account_id:
				if record.amount > record.remaining_value:
					record.amount = 0
					self.env.user.notify_warning(_('There is no Enough Budget'))

	@api.model 
	def create(self,vals):
		vals['name'] = self.env["ir.fields.converter"].text_from_html(vals['name'], 40, 1000, "...")
		return super(RatificationLine, self).create(vals)

	@api.multi
	@api.onchange('the_type')
	def onchange_the_type(self):
		self.ratification_type = 'expenses'
		self.accounts_receivable_types = False
		self.accounts_payable_types = False
		self.account_id = False
		self.analytic_account_id = False

		if self.the_type == 'budget':
			self.ratification_type = 'expenses'
			
		if self.the_type == 'accounts_receivable':
			self.accounts_receivable_types = 'accounts_receivable'
			self.ratification_type = 'accounts_receivable'
			
		if self.the_type == 'accounts_payable':
			self.ratification_type = 'accounts_payable'
			self.accounts_payable_types = 'accounts_payable'
	

	@api.multi
	@api.onchange('accounts_receivable_types')
	def onchange_receivable_types(self):
		if self.accounts_receivable_types:
			self.ratification_type = self.accounts_receivable_types

	@api.multi
	@api.onchange('accounts_payable_types')
	def onchange_payable_types(self):
		if self.accounts_payable_types:
			self.ratification_type = self.accounts_payable_types
	

	@api.multi
	@api.depends('account_id','analytic_account_id')
	def get_budget_amounts(self):
		for record in self:
			if record.account_id:
				for budget in self.env['crossovered.budget'].search([('state','=','validate')]):
					for budget_line in budget.expenses_line_ids:
						if budget_line.analytic_account_id == record.analytic_account_id:
							for buget_detail in budget_line.general_budget_id.accounts_value_ids:
								if buget_detail.account_id == record.account_id:
									record.approved_value = buget_detail.approved_value
									record.remaining_value = buget_detail.remaining_value
			else:
				record.analytic_account_id = False
								

	@api.multi
	@api.onchange('account_id')
	def onchange_account(self):
		for record in self:
			if record.account_id:
				if record.ratification_type in ['expenses']:
					record.analytic_account_id = record.account_id.parent_budget_item_id


	@api.multi
	@api.onchange('ratification_type')
	def onchange_ratification_type(self):
		for record in self:
			if record.ratification_type in ['accounts_receivable','petty_cash','service_provider_loan','prepaid_expenses','purchases']:
				record.analytic_account_id = False

			if record.ratification_type == 'purchases':
				stock_account_ids = []
				for stock in self.env['stock.location'].search([]):
					if stock.account_id :
						stock_account_ids.append( stock.account_id.id )
				return {
					'domain' : {
						'account_id':[('id','in',stock_account_ids)]
					}
				}
			else:

				account_ids = []
				for account in self.env['account.account'].search([('is_group','=','sub_account')]):
					if account.code[:1] in ['2','3','4']:
						account_ids.append( account.id )

				return {
					'domain' : {
						'account_id':[('id','in',account_ids)]
					}
				}
		


class RatificationLineTag(models.Model):
	_name = 'ratification.line.tag'

	tag_id = fields.Many2one('account.analytic.tag', string='Tag')
	amount = fields.Float()
	ratification_line_id = fields.Many2one('ratification.line',ondelete='cascade')

	partner_id = fields.Many2one(related='ratification_line_id.partner_id', string='The Partner', store=True)
	name = fields.Char( related='ratification_line_id.name',string='Description', store=True)
	analytic_account_id = fields.Many2one(related='ratification_line_id.analytic_account_id',string='Budget Item', store=True)
	account_id = fields.Many2one(related='ratification_line_id.account_id', string='Account', store=True)
	cost_center_id = fields.Many2one(related='ratification_line_id.cost_center_id', string='Cost Center', store=True)
	line_amount = fields.Float(related='ratification_line_id.amount', string='Total Amount', store=True)
	ratification_id = fields.Many2one(related='ratification_line_id.ratification_id', store=True)
	branch_id = fields.Many2one(related='ratification_line_id.branch_id', string='Branch', store=True)
	date = fields.Date(related='ratification_line_id.date', store=True)

	the_type = fields.Selection( related='ratification_line_id.the_type' , string="Ratification Type", store=True)

	accounts_receivable_types = fields.Selection( related='ratification_line_id.accounts_receivable_types' , string='Sub Type' , store=True)

	accounts_payable_types = fields.Selection(related='ratification_line_id.accounts_payable_types', string='Sub Type', store=True)

	ratification_type = fields.Selection(related='ratification_line_id.ratification_type', store=True)

	approved_value = fields.Float(related='ratification_line_id.approved_value', store=True)
	remaining_value = fields.Float(related='ratification_line_id.remaining_value', store=True)

	service_levels = fields.Selection(related='ratification_line_id.service_levels', store=True) 
	
	level_id = fields.Many2one(related='ratification_line_id.level_id', store=True) 

	state = fields.Selection(related='ratification_line_id.state', store=True)
	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)






class RatificationLineTaxLine(models.Model):
	_name = 'ratification.line.tax.line'

	name = fields.Char('Description')
	tax_id = fields.Many2one('account.tax', string='Tax/Deduction')
	amount = fields.Float()
	ratification_line_id = fields.Many2one('ratification.line')
	branch_id = fields.Many2one('res.company', string='Branch',default= lambda self:self.env.user.company_id.id)
	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)


	@api.multi
	@api.onchange('tax_id')
	def onchange_tax_id(self):
		if self.tax_id:
			self.name = self.tax_id.name
			tax_amount = 0
			if self.tax_id.amount_type == 'fixed':
				tax_amount = self.tax_id.amount
			if self.tax_id.amount_type == 'percent':
				tax_amount = (self.tax_id.amount / 100)* self.ratification_line_id.amount
			self.amount = tax_amount

	@api.multi
	@api.onchange('tax_id','amount')
	def onchange_tax_or_amount(self):
		self.ratification_line_id.ratification_id.compute_taxs()



class RatificationTaxLine(models.Model):
	_name = 'ratification.tax.line'

	partner_id = fields.Many2one('res.partner')
	name = fields.Char('Description')
	tax_id = fields.Many2one('account.tax', string='Tax/Deduction')
	amount = fields.Float()
	ratification_id = fields.Many2one('ratification.ratification')
	branch_id = fields.Many2one('res.company', string='Branch',default= lambda self:self.env.user.company_id.id)
	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)


	@api.multi
	@api.onchange('tax_id')
	def onchange_tax_id(self):
		tax_amount = 0
		if self.tax_id.amount_type == 'fixed':
			tax_amount = self.tax_id.amount
		if self.tax_id.amount_type == 'percent':
			tax_amount = (self.tax_id.amount / 100)* self.ratification_id.amount
		self.amount = tax_amount




class RatificationLoanLine(models.Model):
	_name = 'ratification.loan.line'

	name = fields.Char('Description')
	loan_date = fields.Date()
	loan_amount = fields.Float()
	is_add_loan = fields.Boolean('Add Loan ?')
	added_amount = fields.Float() 
	ratification_id = fields.Many2one('ratification.ratification')
	branch_id = fields.Many2one('res.company', string='Branch',default= lambda self:self.env.user.company_id.id)
	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)


class RatificationInstallment(models.Model):
	_name = 'ratification.installment'
	_description = 'Service Provider Loan Installment'

	_inherit = ['mail.thread','mail.activity.mixin', 'portal.mixin']

	name = fields.Char(string='Description',track_visibility='always')
	account_id = fields.Many2one('account.account',track_visibility='always')
	date = fields.Date(track_visibility='always')
	amount = fields.Float(track_visibility='always')
	is_paid = fields.Boolean(string='Is Paid ?',track_visibility='always')
	ratification_id = fields.Many2one('ratification.ratification',track_visibility='always')

	state = fields.Selection([], related='ratification_id.state' )

	partner_id = fields.Many2one('res.partner', related='ratification_id.partner_id')
	branch_id = fields.Many2one('res.company', string='Branch',default= lambda self:self.env.user.company_id.id)
	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)
	



	@api.multi
	def show_collection(self):
		return {
			'type' : 'ir.actions.act_window',
			'res_model' : 'collection.collection',
			'view_mode' : 'tree,form',
			'context' : {
				'default_partner_id' : self.partner_id.id,
				'default_ratification_loan_installment_id' : self.id,
				},
			'domain' : [('ratification_loan_installment_id','=',self.id)]
		}




class RatificationPrepaidExpenses(models.Model):
	_name = 'ratification.prepaid.expenses'
	_description = 'Prepaid Expenses'

	_inherit = ['mail.thread','mail.activity.mixin', 'portal.mixin']

	name = fields.Char(string='Description',track_visibility='always')
	account_id = fields.Many2one('account.account', string='Account',track_visibility='always')
	to_account_id = fields.Many2one('account.account', string='Transfer to Account',track_visibility='always', domain=lambda self:self.get_to_account_doamin())
	analytic_account_id = fields.Many2one('account.analytic.account', string='Budget Item',track_visibility='always')
	date = fields.Date(track_visibility='always', related='ratification_id.date')
	due_date = fields.Date(track_visibility='always')
	amount = fields.Float(track_visibility='always')
	is_transfered = fields.Boolean(string='Is Transfered ?',track_visibility='always')
	ratification_id = fields.Many2one('ratification.ratification',track_visibility='always')

	transfer_date = fields.Date(track_visibility='always', default=fields.Date.today())

	state = fields.Selection([], related='ratification_id.state' )
	partner_id = fields.Many2one('res.partner', related='ratification_id.partner_id',track_visibility='always')
	state_id = fields.Selection([('not_transfered','Not Transfered'),('transfered','Transfered'),('canceled','Cancelled')], default='not_transfered', track_visibility='always')
	journal_id = fields.Many2one('account.journal', string='Bank/Cash',track_visibility='always')
	branch_id = fields.Many2one('res.company', string='Branch',default= lambda self:self.env.user.company_id.id,track_visibility='always')
	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)
	

	@api.multi
	def get_to_account_doamin(self):
		account_ids = []
		for account in self.env['account.account'].search([('is_group','=','sub_account')]):
			if account.code[:1] in ['2','3','4']:
				account_ids.append( account.id )
		return [('id','in',account_ids)]



	@api.multi
	@api.onchange('to_account_id')
	def onchange_account(self):
		if self.to_account_id:
			self.analytic_account_id = self.to_account_id.parent_budget_item_id


	@api.multi
	def do_transfer(self):

		if self.analytic_account_id:
			self.env['crossovered.budget'].budget_operations(do_just_check=True, do_reserve=False, do_actual=False, budget_item=self.analytic_account_id, account=self.to_account_id,amount=self.amount,date=self.date)

		move_id = self.env['account.move'].create({
			'name' : self.name,
			'date' : self.transfer_date,
			'journal_id': self.journal_id.id,
			'company_id' : self.branch_id.id,
			'prepaid_expense_id' : self.id,
			'line_ids' : [
				(0,0,{
					'account_id': self.account_id.id ,
					'partner_id' : self.partner_id.id ,
					'name': self.name ,
					'credit' : self.amount,
					'debit' : 0 ,
					}),
				(0,0,{
					'account_id': self.to_account_id.id,
					'partner_id' : self.partner_id.id ,
					'name': self.name ,
					'credit' : 0,
					'analytic_account_id' : self.analytic_account_id.id,
					'debit' : self.amount ,
					})
				],  			
			})
		move_id.post()
		self.is_transfered = True
		self.state_id = 'transfered'

	@api.multi
	def do_cancel_transfer(self):
		for move in self.env['account.move'].search([('prepaid_expense_id','=', self.id)]):
			move.button_cancel()
			move.unlink()
		self.is_transfered = False
		self.state_id = 'canceled'

	@api.multi
	def show_prepaid_expenses_move(self):
		return {
			'type' : 'ir.actions.act_window',
			'res_model' : 'account.move',
			'view_mode' : 'tree,form',
			'context' : {
				'default_prepaid_expense_id' : self.id,
				},
			'domain' : [('prepaid_expense_id','=',self.id)]
		}







class Collection(models.Model):
	_inherit = 'collection.collection'

	ratification_loan_installment_id = fields.Many2one('ratification.installment')

	@api.multi
	def do_confirm(self):
		do_confirm = super(Collection, self).do_confirm()
		if self.ratification_loan_installment_id:
			self.ratification_loan_installment_id.is_paid = True
		return do_confirm 



class AccountMove(models.Model):
	_inherit = 'account.move'

	prepaid_expense_id = fields.Many2one('ratification.prepaid.expenses')


class Journal(models.Model):
	_inherit = 'account.journal'

	update_posted = fields.Boolean(default=True)

class RatificationLevel(models.Model):
	_name = 'ratification.line.level'

	name = fields.Char(string='Description')
	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)


class AccountAnalyticTag(models.Model):
	_inherit = 'account.analytic.tag'

	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)



class ReportLine(models.Model):
	_name = 'ratification.report.line'

	account_id = fields.Many2one('account.account')
	analytic_account_id = fields.Many2one('account.analytic.account')
	amount = fields.Float()


