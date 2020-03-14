# -*- coding: utf-8 -*-

{
    'name': 'BMC Customizations',
    'version': '1.0',
    'summary': 'Purchase and other Customizations',
    'category': 'Purchase',
    'description': '',
    'depends': ['purchase', 'stock', 'product', 'quality',
                'quality_control','approvals', 'sale', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'security/quality.xml',
        'views/quality_view.xml',
        'views/partner_view.xml',
        'report/quality_report_template.xml',
        'report/quality_report.xml',
        'data/mrp_data.xml',
    ],
    'installable': True,
}
