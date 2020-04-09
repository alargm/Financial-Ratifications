{
	
	'name' : 'Kamil Accounting - Financial Ratifications',
	'Author' : 'Alargm Ahmed ',
	'application' : True,
	'sequence' : 0,
	'data':[
		'security/ir.model.access.csv',
		'security/ratification_rules.xml',
		'data/ratification_sequence_view.xml',
		'views/ratification_view.xml',
		'views/ratification_list_view.xml',

		'views/ratification_list_complex_view.xml',

		'views/ratification_loan_installment_view.xml',
		'views/prepaid_expenses_installment_view.xml',
		'views/petty_cash_clearance_view.xml',
		'views/payment_view.xml',

		'views/tags_analysis_view.xml',

		'wizard/wiz_ratification_list.xml',
		'reports/ratification_report.xml',
		'reports/payment_recept_17.xml',
		'reports/petty_cash_report.xml',
		'reports/bank_transfer_report.xml',

		'reports/bank_transfer_report_for_partner.xml',

		'reports/one_percent_tax_report.xml',
		# 'reports/ratification_list_report.xml',
		'reports/wiz_ratification_list_report.xml',

		'reports/cheque_paper_format.xml',
		'reports/cheque_print.xml',
		'reports/counter_cheque_letter_report.xml'


		],
	'depends' : ['base','kamil_accounting_base','account','html_text','kamil_accounting_revenues_collection','stock','web_notify', 'account_cancel','kamil_accounting_money_supply','report_pdf_preview'],
}
