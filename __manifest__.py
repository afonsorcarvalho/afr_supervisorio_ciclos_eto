{
    'name': 'Supervisório Ciclos - ETO',
    'version': '16.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Módulo para gerenciamento de ciclos de ETO',
    'description': """
        Módulo para gerenciamento de ciclos de ETO.
        Permite visualizar e analisar dados de ciclos de ETO.
    """,
    'author': 'Engenapp',
    'website': 'https://www.engenapp.com.br',
    'depends': [
        'afr_supervisorio_ciclos',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/supervisorio_ciclos_form_eto.xml',
        'views/supervisorio_ciclos_tree_eto.xml',
        'views/menu_views.xml',
        'reports/supervisorio_ciclo_reports_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 