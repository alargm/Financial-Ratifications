from odoo import models, fields, api,_ 
from . import amount_to_text as amount_to_text_ar
from datetime import date, datetime
from odoo.exceptions import ValidationError


class Payments(models.Model):
	_name = 'ratification.payment'
	_description = 'The Payments'
	_rec_name = 'ratification_id'
	_order = 'id desc'
	_inherit = ['mail.thread','mail.activity.mixin', 'portal.mixin']

	code = fields.Char('Payment Code', default='/')
	partner_id = fields.Many2one('res.partner', 'Payment for')
	date = fields.Date('Date', default=fields.Date.today())
	amount = fields.Float('Amount', compute='compute_amount',readonly=True)
	amount_in_words = fields.Char(compute='compute_amount' ,track_visibility='always')
	name = fields.Text( related='ratification_id.name',readonly=True)
	currency_id = fields.Many2one('res.currency', 'Currency')
	ratification_id = fields.Many2one('ratification.ratification', 'Ratification',readonly=True)
	payment_type = fields.Selection([('Cheque','Cheque'),('cash','Cash'),('bank_transfer','Bank Transfer'),('counter_cheque','Counter Cheque')], default='Cheque',track_visibility='always')
	check_number = fields.Char('Cheque Number',track_visibility='always')
	branch_id = fields.Many2one('res.company', string='Branch',default= lambda self:self.env.user.company_id.id,track_visibility='always')
	journal_id = fields.Many2one('account.journal', 'Bank/Cash')	
	account_number = fields.Char('Account Number')
	available_balance = fields.Float('Available Balance')
	
	stock_id = fields.Many2one('stock.location', 'Stock')
	stock_account_id = fields.Many2one('account.account', 'Stock Account')
	
	state = fields.Selection([('draft','Draft'),('confirmed','Confirmed'),('approved','Audited'),('canceled','Canceled')], default='draft')

	line_ids = fields.One2many('payment.ratification.line', 'payment_id')
	tax_line_ids = fields.One2many('payment.ratification.tax.line', 'payment_id')
	loan_line_ids = fields.One2many('payment.ratification.loan.line', 'payment_id')

	payment_move_id = fields.Many2one('account.move')

	# total_loan_amount = fields.Float(compute='compute_loans_ids',track_visibility='always')
	# total_loan_amount_in_words = fields.Char(compute='compute_loans_ids',track_visibility='always',string='Loans Amount in Words')

	total_taxes_amount = fields.Float(compute='compute_tax_ids',track_visibility='always')
	total_taxes_amount_in_words = fields.Char(compute='compute_tax_ids',track_visibility='always',string='Taxes Amount in Words')

	net_amount = fields.Float(compute='compute_net_amount',track_visibility='always')
	net_amount_in_words = fields.Char(compute='compute_net_amount',track_visibility='always')

	has_petty_cash = fields.Boolean(related='ratification_id.has_petty_cash')

	deduct_commission = fields.Selection([('account','The Account'),('amount','The Amount')], string="Deduct Commission From", default='account')

	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)
	
	report_line_ids = fields.Many2many('payment.report.line')





	def show_clearance(self):

		for clearance in self.env['ratification.petty.cash.clearance'].search([('ratification_id','=',self.ratification_id.id)]):
			
			return {
				'type' : 'ir.actions.act_window',
				'view_mode' : 'form',
				'res_model' : 'ratification.petty.cash.clearance',
				'res_id' : clearance.id,
				'domain' : [('ratification_id','=', self.ratification_id.id )],
				'context' : {'default_ratification_id':self.ratification_id.id}, 
			}			

		return {
			'type' : 'ir.actions.act_window',
			'view_mode' : 'form',
			'res_model' : 'ratification.petty.cash.clearance',
			'domain' : [('ratification_id','=', self.ratification_id.id )],
			'context' : {'default_ratification_id':self.ratification_id.id}, 
		}


	@api.multi
	def unlink(self):
		for record in self:
			if record.state not in ['draft','canceled']:
				raise ValidationError(_('You Can not delete a Record, witch is not Draft or Canceled'))
			for account_move in self.env['account.move'].search([('ratification_payment_id','in', self.ids)]):
				account_move.button_cancel()
				account_move.unlink()
			return super(Payments, self).unlink()


	@api.multi
	@api.depends('journal_id','date')
	def get_journal_balance(self):
		date_to = fields.Date.today()
		
		date_from = date( date_to.year, 1, 1) 
		
		if self.date:
			date_to = self.date

		if self.journal_id:
			self._cr.execute("select sum(debit)-sum(credit) from account_move_line where account_id="  + str(self.journal_id.default_credit_account_id.id) + " AND date <= '" + str(date_to) + "'  " )
			balance = self.env.cr.fetchone()[0] or 0.0


			str_balance = str('{:,.2f}'.format( balance ) )
			if self.state == 'draft':
				self.env.user.notify_info( str_balance )
			self.available_balance = balance

			if self.journal_id.type == 'bank':
				self.account_number = self.journal_id.account_number



	@api.multi
	@api.onchange('payment_type')
	def onchange_payment_type(self):
		# if self.
		for record in self:
			
			if record.payment_type == 'bank_transfer':
				# record.check_number = self.env['ir.sequence'].next_by_code( 'bank.transfer.sequence' )
					if record.date:
						seq_code = 'payment.bank.transfer.sequence.' + str(record.date.year) + '.' + str(record.date.month)
						seq = self.env['ir.sequence'].next_by_code( seq_code )
						if not seq:
							self.env['ir.sequence'].create({
								'name' : seq_code,
								'code' : seq_code,
								'prefix' :  str(record.date.year) + '-' +  str(record.date.month) + '-' ,
								'number_next' : 1,
								'number_increment' : 1,
								'use_date_range' : True,
								'padding' : 4,
								})
							seq = self.env['ir.sequence'].next_by_code( seq_code )
						record.check_number = seq 

			if record.payment_type == 'cash':
				record.journal_id = False
				return {
					'domain' : {
						'journal_id':[('type','=','cash')]
					}
				}
			if record.payment_type in ['Cheque','bank_transfer','counter_cheque']:
				record.journal_id = False
				return {
					'domain' : {
						'journal_id':[('type','=','bank')]
					}
				}
			



	@api.multi
	@api.onchange('journal_id')
	def onchange_journal(self):
		for record in self:
			if record.journal_id.type == 'bank':
				record.account_number = record.journal_id.account_number

			date_to = fields.Date.today()
		
			date_from = date( date_to.year, 1, 1) 
			
			if record.date:
				date_to = record.date

			if record.journal_id:
				self._cr.execute("select sum(debit)-sum(credit) from account_move_line where account_id="  + str(record.journal_id.default_credit_account_id.id) + " AND date <= '" + str(date_to) + "'  " )
				balance = self.env.cr.fetchone()[0] or 0.0


				str_balance = str('{:,.2f}'.format( balance ) )
				if record.state == 'draft':
					self.env.user.notify_info( str_balance )
					record.available_balance = balance






	@api.multi
	@api.depends('tax_line_ids')
	def compute_tax_ids(self):
		for record in self:
			total = 0
			for tax_line in record.tax_line_ids:
				total = total + tax_line.amount
			record.total_taxes_amount = total
			record.total_taxes_amount_in_words = amount_to_text_ar.amount_to_text(total, 'ar')



	@api.multi
	@api.depends('line_ids','tax_line_ids')
	def compute_net_amount(self):
		for record in self:
			total = 0
			total_taxes = 0
			total_loans = 0
			
			for total_line in record.line_ids:
				total = total + total_line.amount
			for tax_line in record.tax_line_ids:
				total_taxes = total_taxes + tax_line.amount
			# for loan_line in record.loan_ids:
			# 	if record.has_loan:
			# 		if loan_line.is_add_loan:
			# 			total_loans = total_loans + loan_line.added_amount

			net = total - total_taxes - total_loans
			record.net_amount = net
			record.net_amount_in_words = amount_to_text_ar.amount_to_text(net, 'ar')





	@api.multi
	@api.depends('line_ids')
	def compute_amount(self):
		for record in self:
			total = 0
			for line in record.line_ids:
				total = total + line.amount
			record.amount = total
			record.amount_in_words = amount_to_text_ar.amount_to_text(total, 'ar')


	@api.multi
	def do_canceled(self):
		# self.ratification_id.do_cancel()
		for account_move in self.env['account.move'].search([('ratification_payment_id','=', self.id)]):
			# self.state = 'canceled'
			return {
				'type' : 'ir.actions.act_window',
				'view_mode' : 'form',
				'target': 'new',
				'res_model' : 'wizard.payment.cancel',				
				'context' : {'payment_id':self.id}, 
			}		

			# account_move.button_cancel()
			# account_move.unlink()
		self.state = 'canceled'

	@api.multi
	def do_set_to_draft(self):
		self.state = 'draft'

	@api.multi
	def do_confirm(self):
		for record in self:

			if len(record.line_ids) < 1:
				raise ValidationError(_('Please Add Details!'))

			date_to = fields.Date.today()

			if record.date:
				date_to = record.date

			if record.journal_id:
				self._cr.execute("select sum(debit)-sum(credit) from account_move_line where account_id="  + str(self.journal_id.default_credit_account_id.id) + " AND date <= '" + str(date_to) + "'  " )
				balance = self.env.cr.fetchone()[0] or 0.0

				if record.amount > balance:
					raise ValidationError(_('There is no enough balance'))


			found = False
			for account_move in self.env['account.move'].search([('ratification_payment_id','=', self.id)]):
				found = True
			if not found:
				self.do_create()

			record.ratification_id.state = 'payment_confirmed'

			record.state = 'confirmed'
			record.ratification_id.state = 'paid'


	@api.multi
	def do_create(self):
		for record in self:

			taxes = []
			if record.ratification_id.ratification_list_id:
				for ratification_line in record.ratification_id.ratification_list_id.ratification_line_ids:
					for line in ratification_line.deduction_ids:
						if line.tax_id:
							if line.tax_id.account_id:
								taxes.append({
									'account_id': line.tax_id.account_id.id,
									'account_name': line.tax_id.account_id.name,
									'amount' : line.amount,
									'partner_id' :  line.ratification_line_id.partner_id.id,
								 })

				for line in record.ratification_id.ratification_list_id.other_deduction_ids:
					if line.tax_id:
						if line.tax_id.account_id:
							taxes.append({
								'account_id': line.tax_id.account_id.id,
								'account_name': line.tax_id.account_id.name,
								'amount' : line.amount,
								'partner_id' :  line.partner_id.id,
							})

			else:
				for ratification_line in record.ratification_id.line_ids:
					for line in ratification_line.deduction_ids:
						if line.tax_id:
							if line.tax_id.account_id:
								taxes.append({
									'account_id': line.tax_id.account_id.id,
									'account_name': line.tax_id.account_id.name,
									'amount' : line.amount,
									'partner_id' :  record.ratification_id.partner_id.id,
								 })


			tax_amount = 0
			for tax_line in record.tax_line_ids:
				tax_amount = tax_amount + tax_line.amount

			total_amount = 0
			for line in record.line_ids:
				total_amount = total_amount + line.amount

			percentage_amount = tax_amount / total_amount * 100

			move_id = self.create_move(
				ref=record.name, 
				journal_id=record.journal_id.id,
				payment_id=record.id,
				date=record.date)

			# credit_line = self.create_move_line(
			# 	name=record.name,
			# 	partner_id = record.partner_id.id, 
			# 	move_id=move_id.id, 
			# 	account_id=  record.journal_id.default_credit_account_id.id,
			# 	credit= record.amount - tax_amount,
			# 	amount_currency=False,
			# 	currency_id=False,
			# 	date=record.date)

			partner_id = record.partner_id.id  or None

			if not record.journal_id.default_credit_account_id:
				raise ValidationError(_('Please Add Account to ' + record.journal_id.name ))


			self._cr.execute(
			
			""" 
				INSERT INTO ACCOUNT_MOVE_LINE(name,partner_id,move_id,account_id,credit,date_maturity,date,company_id,create_uid) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)	
			""", (str(record.name), partner_id, move_id.id, record.journal_id.default_credit_account_id.id, (record.amount - tax_amount),str(record.date),str(record.date),self.env.user.company_id.id,self.env.user.id))

			for tax_line in taxes:
				self._cr.execute(				
				""" 
					INSERT INTO ACCOUNT_MOVE_LINE(name,partner_id,move_id,account_id,credit,date_maturity,date,company_id,create_uid) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)	
				""", (str(tax_line['account_name']), tax_line['partner_id'], move_id.id, tax_line['account_id'], tax_line['amount'],str(record.date),str(record.date),self.env.user.company_id.id,self.env.user.id))




			# for tax_line in record.tax_line_ids:
				
			# 	# debit_line = self.create_move_line(
			# 	# 	name=tax_line.name,
			# 	# 	partner_id=tax_line.partner_id.id, 
			# 	# 	move_id=move_id.id, 
			# 	# 	account_id=tax_line.tax_id.account_id.id, 
			# 	# 	credit=tax_line.amount, 
			# 	# 	amount_currency=False,
			# 	# 	currency_id=False)

			# 	partner_id = tax_line.partner_id.id or record.partner_id.id or None



			# 	if not tax_line.tax_id:
			# 		raise ValidationError(_('Please Add Valid Info in Deductions '))

			# 	if tax_line.tax_id:
			# 		self._cr.execute(
					
			# 		""" 
			# 			INSERT INTO ACCOUNT_MOVE_LINE(name,partner_id,move_id,account_id,credit,date_maturity,date,company_id,create_uid) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)	
			# 		""", (str(tax_line.name), partner_id, move_id.id, tax_line.tax_id.account_id.id, tax_line.amount,str(record.date),str(record.date),self.env.user.company_id.id,self.env.user.id))

			
			for line in record.line_ids:

				tax_line_amount = line.amount *  percentage_amount / 100 
				net_amount = line.amount - tax_line_amount

				budget_item = line.analytic_account_id.id
				if record.ratification_id.ratification_type in ['petty_cash']:
					budget_item = None
				if not budget_item:
					budget_item = None
				

				cost_center_id = None
				if line.cost_center_id:
					cost_center_id = line.cost_center_id.id

				partner_id = line.partner_id.id or record.partner_id.id or None

				# debit_line = self.create_move_line(
				# 	name=line.name,
				# 	partner_id= line.partner_id.id or record.partner_id.id, 
				# 	move_id=move_id.id, 
				# 	account_id=line.account_id.id, 
				# 	debit=line.amount, 
				# 	amount_currency=False,
				# 	currency_id=False,
				# 	analytic_account_id=budget_item, 
				# 	analytic_tag_ids = [(6,0, line.analytic_tag_ids._ids )],
				# 	cost_center_id=line.cost_center_id.id)



				if not line.account_id:
					raise ValidationError(_('Please Add Account to ' + line.name))
				
				self._cr.execute(				
				""" 
					INSERT INTO ACCOUNT_MOVE_LINE(name,partner_id,move_id,account_id,debit,analytic_account_id,cost_center_id,date_maturity,date,company_id,create_uid) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)	
				""", (str(line.name), partner_id, move_id.id, line.account_id.id, line.amount, budget_item, cost_center_id,str(record.date),str(record.date),self.env.user.company_id.id,self.env.user.id))


				self._cr.execute(				
				""" 
					UPDATE ACCOUNT_MOVE SET amount = %s WHERE id = %s
				""",(total_amount, move_id.id) )

			move_id.post()

			for line in record.line_ids:
				if line.analytic_account_id:
					self.env['crossovered.budget'].budget_operations(do_just_check=False, do_reserve=False, do_actual=True, budget_item=line.analytic_account_id, account=line.account_id,amount=line.amount,date=record.date)
			
			record.payment_move_id = move_id.id

			record.ratification_id.state = 'paid'

			for prepaid_expense_line in record.ratification_id.prepaid_expenses_installment_ids:
				if not prepaid_expense_line.journal_id:
					prepaid_expense_line.journal_id = record.journal_id.id


			report_line_list = []
			account_ids = []
			for line in record.payment_move_id.line_ids:
				if line.account_id.id not in account_ids:
					account_ids.append( line.account_id.id )
					report_line_list.append( {'name' : line.account_id.name,'account_id' : line.account_id.id , 'analytic_account_id':line.analytic_account_id.id, 'debit_amount' : line.debit, 'credit_amount' : line.credit  } )
				else:
					for row in report_line_list:
						if row['account_id'] == line.account_id.id:

							row['credit_amount'] = row['credit_amount'] + line.credit
							
							row['debit_amount'] = row['debit_amount'] + line.debit

			record.report_line_ids = False
			for row in report_line_list:
				record.report_line_ids = [(0,0,{
					'account_id' : row['account_id'],
					'debit_amount' : row['debit_amount'],
					'credit_amount' : row['credit_amount'],
					'analytic_account_id' : row['analytic_account_id'],
					})]



	@api.multi
	def do_approve(self):
		for record in self:

			
			record.state = 'approved'





		
	@api.multi
	def do_cancel(self):
		pass

	@api.multi
	@api.onchange('ratification_id')
	def onchange_ratification(self):
		for record in self:
			record.line_ids = False
			record.tax_line_ids = False

			if record.ratification_id:
				
				record.partner_id = record.ratification_id.partner_id.id
				record.branch_id = record.ratification_id.state_id
				record.payment_type = record.ratification_id.payment_type
				record.currency_id = record.ratification_id.currency_id
				record.branch_id = record.ratification_id.state_id
				# record.date = record.ratification_id.date


				lines = []				
				


				self._cr.execute( "DELETE FROM payment_ratification_line WHERE ratification_id = " + str(record.ratification_id.id) + " " )


				for line in record.ratification_id.line_ids:		
				
					# print('########### line = ', line)
					# lines.append((0,0,{
					# 	'partner_id' : line.partner_id,
					# 	'name' : line.name,
					# 	'analytic_account_id' : line.analytic_account_id.id,
					# 	'account_id' : line.account_id.id,
					# 	'cost_center_id' : line.cost_center_id.id,
					# 	'amount' : line.amount,
					# 	'analytic_tag_ids' : [(6,0, line.analytic_tag_ids._ids )],
					# 	'branch_id' : line.branch_id.id,
					# 	'ratification_type' : line.ratification_type,
					# 	'accounts_receivable_types': line.accounts_receivable_types ,
					# 	'accounts_payable_types': line.accounts_payable_types,
					# 	'account_code' : line.account_code,
					# 	}))

				# record.line_ids = lines


					self._cr.execute(
					""" 
						INSERT INTO payment_ratification_line(partner_id,name,analytic_account_id,account_id,cost_center_id,amount,branch_id,ratification_type,accounts_receivable_types,accounts_payable_types,account_code,ratification_id,company_id,create_uid) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)	
					""", ( (line.partner_id.id or None) , (str(line.name) or None), (line.analytic_account_id.id or None) ,(line.account_id.id or None), (line.cost_center_id.id or None), (line.amount or None),(line.branch_id.id or None),(line.ratification_type or None),(line.accounts_receivable_types or None),(line.accounts_payable_types or None),(line.account_code or None),record.ratification_id.id,self.env.user.company_id.id,self.env.user.id))

				ids = self.env['payment.ratification.line'].search([('ratification_id','=',record.ratification_id.id)])._ids

				record.line_ids = [(6,0, ids )]

				for line in record.ratification_id.tax_ids:
					record.tax_line_ids = [(0,0,{
						'partner_id' : line.partner_id,
						'name' : line.name,
						'tax_id' : line.tax_id.id,
						'amount' : line.amount,
						})]

				for line in record.ratification_id.loan_ids:
					if line.is_add_loan:
						record.loan_line_ids = [(0,0,{
							'name' : line.name,
							'loan_date' : line.loan_date,
							'is_add_loan': line.is_add_loan,
							'added_amount': line.added_amount,
							})]
						
	@api.model 
	def create(self, vals):
		create_id = super(Payments, self).create(vals)
		if create_id.date:
			seq_code = 'payment.sequence.' + str(create_id.date.year) + '.' + str(create_id.date.month)
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
			create_id.code = seq 

			create_id.do_confirm()
			
			# create_id.do_create()	


			create_id.ratification_id.state = 'payment_created'
			create_id.state = 'draft'



		return create_id


	@api.multi 
	def write(self, vals):
		write_id = super(Payments, self).write(vals)
		if vals.get('date', False):
			seq_code = 'payment.sequence.' + str(self.date.year) + '.' + str(self.date.month)
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
			self.code = seq 
		return write_id



	def create_move(self, ref, journal_id,payment_id=False, date=False):
		move = self.env['account.move']
		vals = {
		'ref': ref,
		'journal_id': journal_id,
		'ratification_payment_id' : payment_id,
		'date' : date,
		'document_number' : self.check_number or ref,
		}
		return move.create(vals)


	def create_move_line(self, partner_id=False, name=False, move_id=False, account_id=False, debit=False, credit=False, date=False, amount_currency=False, currency_id=False, analytic_account_id=False, analytic_tag_ids=False,cost_center_id=False):
		move_line = self.env['account.move.line']
		vals = {
			'partner_id': partner_id,
			'name': name,
			'move_id': move_id,
			'account_id': account_id,
			'debit': debit,
			'credit': credit,
			'date_maturity' : date,
			'amount_currency' : amount_currency,
			'currency_id' : currency_id,
			'analytic_account_id' : analytic_account_id, 
			'analytic_tag_ids': analytic_tag_ids,
			'cost_center_id': cost_center_id,
		}
		return move_line.with_context(check_move_validity=False).create(vals)



	@api.multi
	def show_payment_moves(self):
		return {
			'type' : 'ir.actions.act_window',
			'view_mode' : 'tree,form',
			'res_model' : 'account.move',
			'domain' : [('ratification_payment_id','=', self.id )],
		}



class PaymentRatificationLine(models.Model):
	_name = 'payment.ratification.line'


	partner_id = fields.Many2one('res.partner')
	name = fields.Char(string='Description')
	analytic_account_id = fields.Many2one('account.analytic.account',string='Budget Item')
	account_id = fields.Many2one('account.account', string='Account')
	cost_center_id = fields.Many2one('kamil.account.cost.center', string='Cost Center')
	analytic_tag_ids = fields.Many2many('account.analytic.tag',string='Analytic Tags')
	amount = fields.Float()
	payment_id = fields.Many2one('ratification.payment')
	branch_id = fields.Many2one('res.company', string='Branch',default= lambda self:self.env.user.company_id.id,track_visibility='always')
	payment_branch_id = fields.Many2one('res.company', related='payment_id.branch_id', string='Branch')
	parent_branch_id = fields.Many2one('res.company', string='Branch')

	ratification_type = fields.Selection([
		('expenses','expenses'),
		('purchases','Purchases'),
		('accounts_receivable','Accounts Receivable'),
		('petty_cash','Petty Cash'),
		('service_provider_loan','Service Provider Loans'),
		('prepaid_expenses', 'Prepaid Expenses'),
		('accounts_payable','Accounts Payable'),
		('service_provider_claim','Service Provider Claim')],default='expenses',track_visibility='always')
		
	accounts_receivable_types = fields.Selection([
		('accounts_receivable','Accounts Receivable'),
		('petty_cash','Petty Cash'),
		('service_provider_loan','Service Provider Loans'),
		('prepaid_expenses', 'Prepaid Expenses')], default='accounts_receivable', string='Sub Type' )

	accounts_payable_types = fields.Selection([
		('accounts_payable','Accounts Payable'),
		('service_provider_claim','Service Provider Claim')],default='accounts_payable', string='Sub Type')

	item_type = fields.Selection([('medicine','Medicine'),('labs','Labs'),('transformed','Transformed'),('other','Other')],default='other')
	account_code = fields.Char()

	ratification_id = fields.Many2one('ratification.ratification')

	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)
	

class PaymentRatificationTaxLine(models.Model):
	_name = 'payment.ratification.tax.line'

	partner_id = fields.Many2one('res.partner')
	name = fields.Char('Description')
	tax_id = fields.Many2one('account.tax', string='Tax/Deduction')
	amount = fields.Float()
	payment_id = fields.Many2one('ratification.payment')

	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)
	



class PaymentRatificationLoanLine(models.Model):
	_name = 'payment.ratification.loan.line'

	name = fields.Char('Description')
	loan_date = fields.Date()
	loan_amount = fields.Float()
	is_add_loan = fields.Boolean('Add Loan ?')
	added_amount = fields.Float() 
	payment_id = fields.Many2one('ratification.payment')
	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)
	



class AccountMove(models.Model):
	_inherit = 'account.move'

	ratification_payment_id = fields.Many2one('ratification.payment')
	document_number = fields.Char(default='-')











# class AccountPaymentRegisterLine(models.Model):
# 	_name = 'account.payment.register.line'
# 	_description = 'Account Payment Register Line'

# 	name = fields.Char('Description')
# 	account_analytic_id = fields.Many2one('account.analytic.account')
# 	item_id = fields.Many2one('account.payment.register.item', 'Item')
# 	account_id = fields.Many2one('account.account', 'Account')
# 	amount = fields.Float('Amount')
# 	register_id = fields.Many2one('account.payment.register')


# class AccountPaymentRegisterItem(models.Model):
# 	_name = 'account.payment.register.item'
# 	_description = 'Account Payment Register Item'

# 	name = fields.Char('Name')


class ReportLine(models.Model):
	_name = 'payment.report.line'

	account_id = fields.Many2one('account.account')
	analytic_account_id = fields.Many2one('account.analytic.account')
	amount = fields.Float()
	debit_amount = fields.Float()
	credit_amount = fields.Float()



class CancelPaymenWizard(models.TransientModel):
	_name = 'wizard.payment.cancel'
	
	date = fields.Date('Reverse Entry Date',default=fields.date.today() )

	@api.multi
	def do_cancel(self):

		for account_move in self.env['account.move'].search([('ratification_payment_id','=', self.env.context.get('payment_id',0))]):
			
			copy_move = account_move.copy()
			
			copy_move.date = self.date
			copy_move.name = _('عكس القيد --> ') + str(copy_move.name)
			copy_move.ref = _('عكس القيد --> ') + str(copy_move.ref)
			copy_move.line_ids = False

			lines = []

			for line in account_move.line_ids:
				
				lines.append( (0,0,{
					'account_id' : line.account_id.id,
					'partner_id' : line.partner_id.id,
					'name' :  _('عكس القيد -- ') + line.name,
					'analytic_account_id' : line.analytic_account_id.id,
					'debit' : line.credit,
					'credit' : line.debit,
					'date_maturity' : self.date,
					'date' : self.date,
					}) )

			copy_move.line_ids = lines
			copy_move.post()


		for payment in self.env['ratification.payment'].search([('id','=',  self.env.context.get('payment_id',0) )]):
			payment.state = 'canceled'
			payment.ratification_id.do_cancel()
