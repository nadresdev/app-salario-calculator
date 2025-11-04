import streamlit as st
import datetime
import base64
from datetime import timedelta

# Manejo de importaciones
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import gspread
    from google.oauth2.service_account import Credentials
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False

# REGLAS Y TARIFAS (Centralizadas para fácil mantenimiento)
REGLAS_TARIFAS = {
    "hora_normal": 15500,
    "tarifa_6_horas": 100000,
    "recargos_disponibles": {
        "Ninguno": 0,
        "$5,000": 5000,
        "$10,000": 10000,
        "$15,000": 15000,
        "$20,000": 20000,
        "$25,000": 25000,
        "$40,000": 40000
    },
    "descripciones": {
        "menos_6_horas": "Menos de 6 horas: Horas trabajadas × $15,500",
        "exacto_6_horas": "Exactamente 6 horas: $100,000 fijos",
        "mas_6_horas": "Más de 6 horas: $100,000 + (horas extra × $15,500)",
        "recargos": "Recargos: Se suman al pago base según corresponda"
    }
}

def obtener_rango_semana(fecha_referencia=None):
    """Obtiene el rango de fechas de la semana (lunes a domingo)"""
    if fecha_referencia is None:
        fecha_referencia = datetime.datetime.now()
    elif isinstance(fecha_referencia, datetime.date):
        fecha_referencia = datetime.datetime.combine(fecha_referencia, datetime.time())
    
    # Encontrar el lunes de esta semana
    lunes = fecha_referencia - timedelta(days=fecha_referencia.weekday())
    domingo = lunes + timedelta(days=6)
    return lunes, domingo

def selector_semana():
    """Crea un selector de semana personalizado"""
    st.markdown("### 📅 Selecciona la Semana")
    
    # Opciones para seleccionar semana
    opciones_semana = {
        "Esta semana": datetime.datetime.now(),
        "Semana pasada": datetime.datetime.now() - timedelta(days=7),
        "Hace 2 semanas": datetime.datetime.now() - timedelta(days=14),
        "Hace 3 semanas": datetime.datetime.now() - timedelta(days=21),
        "Semana próxima": datetime.datetime.now() + timedelta(days=7),
        "Selección manual": "manual"
    }
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        seleccion = st.selectbox(
            "Selecciona una semana:",
            options=list(opciones_semana.keys()),
            index=0,
            key="selector_semana"
        )
    
    fecha_seleccionada = None
    
    if seleccion == "Selección manual":
        with col2:
            # Selector de fecha para semana específica
            fecha_seleccionada = st.date_input(
                "Selecciona cualquier día de la semana:",
                value=datetime.datetime.now(),
                key="fecha_manual"
            )
    else:
        fecha_seleccionada = opciones_semana[seleccion]
    
    # Obtener rango de la semana seleccionada
    lunes, domingo = obtener_rango_semana(fecha_seleccionada)
    
    # Mostrar información de la semana seleccionada
    st.info(f"**📅 Semana seleccionada:** {lunes.strftime('%d/%m/%Y')} - {domingo.strftime('%d/%m/%Y')}")
    
    return lunes, domingo

def mostrar_reglas_tarifas():
    """Muestra las reglas y tarifas en la interfaz"""
    with st.container():
        st.markdown("---")
        st.markdown("### 📊 REGLAS Y TARIFAS APLICADAS")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💰 Tarifas Actuales")
            st.markdown(f"""
            - **Hora normal:** `${REGLAS_TARIFAS['hora_normal']:,.0f}`
            - **6 horas completas:** `${REGLAS_TARIFAS['tarifa_6_horas']:,.0f}`
            - **Horas extra:** `${REGLAS_TARIFAS['hora_normal']:,.0f}` c/u
            """)
            
        with col2:
            st.markdown("#### 📝 Reglas de Cálculo")
            st.markdown("""
            - **Menos de 6 horas:** Horas × $15,500
            - **Exactamente 6 horas:** $100,000 fijos  
            - **Más de 6 horas:** $100,000 + (horas extra × $15,500)
            - **Recargos:** Se suman al pago base
            """)
        
        st.markdown("#### 🎯 Recargos Disponibles")
        recargos_html = "".join([f'<span style="background-color: #52FA0A; padding: 4px 8px; margin: 2px; border-radius: 4px; display: inline-block;">{key}</span>' for key in REGLAS_TARIFAS['recargos_disponibles'].keys()])
        st.markdown(f'<div style="margin: 10px 0;">{recargos_html}</div>', unsafe_allow_html=True)

def formato_horas_minutos(minutos_totales):
    """Convierte minutos totales a formato hh:mm"""
    if minutos_totales == 0:
        return "00:00"
    horas = int(minutos_totales // 60)
    minutos = int(minutos_totales % 60)
    return f"{horas:02d}:{minutos:02d}"

def crear_formulario_horarios(lunes, domingo):
    """Crea los controles de horarios sin formulario para permitir reruns automáticos"""
    
    # Inicializar session state para esta semana si no existe
    semana_key = f"{lunes.strftime('%Y%m%d')}_{domingo.strftime('%Y%m%d')}"
    
    if f'form_data_{semana_key}' not in st.session_state:
        st.session_state[f'form_data_{semana_key}'] = {
            'horarios': {},
            'recargos': {},
            'sin_trabajo': {}
        }
    
    form_data = st.session_state[f'form_data_{semana_key}']
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    
    registros_semana = []
    horarios_completos = {}
    
    # Crear columnas para los días
    cols = st.columns(2)
    
    for i, dia in enumerate(dias_semana):
        with cols[i % 2]:
            # Mostrar fecha específica para cada día
            fecha_dia = lunes + timedelta(days=i)
            
            # Checkbox para día sin trabajo (siempre visible) - POR DEFECTO DESELECCIONADO
            sin_trabajo_key = f"sin_trabajo_{semana_key}_{i}"
            sin_trabajo = st.checkbox(
                f"❌ {dia} - {fecha_dia.strftime('%d/%m/%Y')} - Día sin trabajo", 
                value=form_data['sin_trabajo'].get(dia, False),  # Por defecto False (deseleccionado)
                key=sin_trabajo_key
            )
            
            # ACTUALIZADO: Si está marcado como sin trabajo, mostrar solo mensaje y deshabilitar completamente
            if sin_trabajo:
                # DÍA SIN TRABAJO - Mostrar mensaje estático sin expander
                st.info("📝 **Este día está marcado como sin trabajo.** Desmarca la casilla para ingresar horarios.")
                
                # Usar valores por defecto para horarios y recargo
                hora_entrada = datetime.time(0, 0)
                hora_salida = datetime.time(0, 0)
                recargo = 0
                
            else:
                # DÍA CON TRABAJO - Expander siempre expandido y funcional
                with st.expander(f"✅ {dia} - {fecha_dia.strftime('%d/%m/%Y')} - Día laboral", expanded=True):
                    # Selectores de hora
                    st.markdown("**Horario:**")
                    col_entrada, col_salida = st.columns(2)
                    
                    with col_entrada:
                        # Selector de hora entrada
                        hora_default = form_data['horarios'].get(f"{dia}_entrada", datetime.time(8, 0))
                        hora_entrada = st.time_input(
                            "Entrada",
                            value=hora_default,
                            key=f"entrada_{semana_key}_{i}"
                        )
                    
                    with col_salida:
                        # Selector de hora salida
                        hora_default = form_data['horarios'].get(f"{dia}_salida", datetime.time(17, 0))
                        hora_salida = st.time_input(
                            "Salida",
                            value=hora_default,
                            key=f"salida_{semana_key}_{i}"
                        )
                    
                    # Selector de recargo
                    recargo_default = form_data['recargos'].get(dia, "Ninguno")
                    recargo_seleccionado = st.selectbox(
                        f"Recargo {dia}",
                        options=list(REGLAS_TARIFAS['recargos_disponibles'].keys()),
                        index=list(REGLAS_TARIFAS['recargos_disponibles'].keys()).index(recargo_default),
                        key=f"recargo_{semana_key}_{i}"
                    )
                    recargo = REGLAS_TARIFAS['recargos_disponibles'][recargo_seleccionado]
                    
                    # Guardar horarios completos
                    horarios_completos[dia] = {
                        'entrada': hora_entrada,
                        'salida': hora_salida
                    }
                    
                    # Actualizar form_data
                    form_data['horarios'][f"{dia}_entrada"] = hora_entrada
                    form_data['horarios'][f"{dia}_salida"] = hora_salida
                    form_data['recargos'][dia] = recargo_seleccionado
            
            # Actualizar estado de día sin trabajo
            form_data['sin_trabajo'][dia] = sin_trabajo
            
            # Calcular horas trabajadas en minutos
            if sin_trabajo:
                minutos_trabajados = 0
                horas_trabajadas = 0
                # Forzar recargo a 0 cuando es día sin trabajo
                recargo = 0
            else:
                minutos_entrada = hora_entrada.hour * 60 + hora_entrada.minute
                minutos_salida = hora_salida.hour * 60 + hora_salida.minute
                
                if minutos_salida >= minutos_entrada:
                    minutos_trabajados = minutos_salida - minutos_entrada
                else:
                    minutos_trabajados = (24 * 60 - minutos_entrada) + minutos_salida
                
                horas_trabajadas = minutos_trabajados / 60
            
            # Calcular pago del día
            pago_total, descripcion, pago_base = calcular_pago_dia(horas_trabajadas, recargo)
            
            # Guardar registro con formato hh:mm
            registro = {
                'dia': dia,
                'minutos_trabajados': minutos_trabajados,
                'horas_formato': formato_horas_minutos(minutos_trabajados),
                'horas_decimal': horas_trabajadas,
                'pago_base': pago_base,
                'pago_total': pago_total,
                'recargo': recargo,
                'descripcion': descripcion,
                'sin_trabajo': sin_trabajo
            }
            registros_semana.append(registro)
    
    # Botones de acción fuera del flujo principal
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("💾 Guardar Horarios", use_container_width=True):
            st.session_state[f'form_data_{semana_key}'] = form_data
            st.session_state[f'horarios_guardados_{semana_key}'] = True  # Marcar como guardado
            st.success("✅ Horarios guardados (listos para calcular)")
    
    with col2:
        if st.button("🗑️ Limpiar Horarios", use_container_width=True):
            # Limpiar form_data para esta semana
            st.session_state[f'form_data_{semana_key}'] = {
                'horarios': {},
                'recargos': {},
                'sin_trabajo': {}
            }
            st.session_state[f'horarios_guardados_{semana_key}'] = False  # Marcar como no guardado
            st.info("🗑️ Horarios limpiados")
            st.rerun()  # Forzar actualización para limpiar inmediatamente
    
    # Actualizar siempre el session_state con los datos actuales
    st.session_state[f'form_data_{semana_key}'] = form_data
    
    # Si no se ha enviado el formulario, usar los datos guardados
    if form_data['horarios']:
        return registros_semana, horarios_completos, False
    else:
        return [], {}, False

def calcular_pago_dia(horas_trabajadas, recargo):
    """Calcula el pago del día según las reglas establecidas"""
    HORA_NORMAL = REGLAS_TARIFAS['hora_normal']
    TARIFA_6_HORAS = REGLAS_TARIFAS['tarifa_6_horas']
    
    if horas_trabajadas == 0:
        return 0, "Día sin trabajo", 0
    elif horas_trabajadas < 6:
        pago_base = horas_trabajadas * HORA_NORMAL
        return pago_base + recargo, f"Horas normales ({horas_trabajadas:.2f}h)", pago_base
    elif horas_trabajadas == 6:
        return TARIFA_6_HORAS + recargo, "6 horas completas", TARIFA_6_HORAS
    else:
        horas_extra = horas_trabajadas - 6
        pago_base = TARIFA_6_HORAS + (horas_extra * HORA_NORMAL)
        return pago_base + recargo, f"6h + {horas_extra:.2f}h extra", pago_base

def generar_pdf(registros_semana, total_semanal, horarios_completos, lunes_semana, domingo_semana):
    """Genera un PDF con el reporte detallado incluyendo reglas y tarifas"""
    if not PDF_AVAILABLE:
        return None
    
    try:
        pdf = FPDF()
        pdf.add_page()
        
        fecha_generacion = datetime.datetime.now()
        
        # Título con rango de fechas
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'REPORTE DE SALARIO SEMANAL', new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(2)
        
        # Rango de fechas de la semana
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f'Semana: {lunes_semana.strftime("%d/%m/%Y")} - {domingo_semana.strftime("%d/%m/%Y")}', new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(2)
        
        # Fecha y hora de generación
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 10, f'Generado el: {fecha_generacion.strftime("%d/%m/%Y a las %H:%M")}', new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(10)
        
        # SECCIÓN MEJORADA: REGLAS Y TARIFAS EN PDF
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'REGLAS Y TARIFAS APLICADAS:', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        # Tarifas
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'TARIFAS:', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f"- Hora normal: ${REGLAS_TARIFAS['hora_normal']:,.0f}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"- 6 horas completas: ${REGLAS_TARIFAS['tarifa_6_horas']:,.0f}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"- Horas extra: ${REGLAS_TARIFAS['hora_normal']:,.0f} c/u", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        # Reglas
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'REGLAS DE CALCULO:', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Arial', '', 10)
        reglas = [
            REGLAS_TARIFAS['descripciones']['menos_6_horas'],
            REGLAS_TARIFAS['descripciones']['exacto_6_horas'],
            REGLAS_TARIFAS['descripciones']['mas_6_horas'],
            REGLAS_TARIFAS['descripciones']['recargos']
        ]
        
        for regla in reglas:
            pdf.cell(0, 6, regla, new_x="LMARGIN", new_y="NEXT")
        
        # Recargos
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'RECARGOS DISPONIBLES:', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Arial', '', 10)
        recargos_texto = ", ".join(REGLAS_TARIFAS['recargos_disponibles'].keys())
        pdf.cell(0, 6, recargos_texto, new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(10)
        
        # Tabla de datos
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'DETALLE POR DIA:', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        # Encabezados de tabla
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(25, 10, 'DIA', border=1, align='C')
        pdf.cell(25, 10, 'FECHA', border=1, align='C')
        pdf.cell(20, 10, 'ENTRADA', border=1, align='C')
        pdf.cell(20, 10, 'SALIDA', border=1, align='C')
        pdf.cell(20, 10, 'HORAS', border=1, align='C')
        pdf.cell(30, 10, 'PAGO BASE', border=1, align='C')
        pdf.cell(25, 10, 'RECARGO', border=1, align='C')
        pdf.cell(35, 10, 'TOTAL DIA', border=1, new_x="LMARGIN", new_y="NEXT", align='C')
        
        # Datos de la tabla
        pdf.set_font('Arial', '', 9)
        
        for i, registro in enumerate(registros_semana):
            # Calcular fecha específica para cada día
            fecha_dia = lunes_semana + timedelta(days=i)
            fecha_dia_str = fecha_dia.strftime('%d/%m/%Y')
            
            dia = registro['dia']
            if dia in horarios_completos and not registro['sin_trabajo']:
                # Formatear hora en formato 12h AM/PM para el PDF
                entrada = horarios_completos[dia]['entrada']
                salida = horarios_completos[dia]['salida']
                
                entrada_str = entrada.strftime('%I:%M %p').lstrip('0')
                salida_str = salida.strftime('%I:%M %p').lstrip('0')
            else:
                entrada_str = "---"
                salida_str = "---"
            
            pdf.cell(25, 10, registro['dia'][:7], border=1, align='C')
            pdf.cell(25, 10, fecha_dia_str, border=1, align='C')
            pdf.cell(20, 10, entrada_str, border=1, align='C')
            pdf.cell(20, 10, salida_str, border=1, align='C')
            pdf.cell(20, 10, registro['horas_formato'], border=1, align='C')  # Usar formato hh:mm
            pdf.cell(30, 10, f"${registro['pago_base']:,.0f}", border=1, align='C')
            pdf.cell(25, 10, f"${registro['recargo']:,.0f}", border=1, align='C')
            pdf.cell(35, 10, f"${registro['pago_total']:,.0f}", border=1, new_x="LMARGIN", new_y="NEXT", align='C')
        
        pdf.ln(10)
        
        # CALCULAR TOTAL DE HORAS TRABAJADAS EN MINUTOS
        total_minutos_trabajados = sum(registro['minutos_trabajados'] for registro in registros_semana)
        total_horas_formato = formato_horas_minutos(total_minutos_trabajados)
        
        # Totales
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f'TOTAL SEMANAL: ${total_semanal:,.0f} COP', new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, f'TOTAL HORAS TRABAJADAS: {total_horas_formato}', new_x="LMARGIN", new_y="NEXT", align='C')
        
        # Análisis detallado
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'ANALISIS DETALLADO:', new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Arial', '', 10)
        
        for i, registro in enumerate(registros_semana, 1):
            fecha_dia = lunes_semana + timedelta(days=i-1)
            fecha_dia_str = fecha_dia.strftime('%d/%m/%Y')
            
            dia = registro['dia']
            if dia in horarios_completos and not registro['sin_trabajo']:
                entrada = horarios_completos[dia]['entrada']
                salida = horarios_completos[dia]['salida']
                entrada_str = entrada.strftime('%I:%M %p').lstrip('0')
                salida_str = salida.strftime('%I:%M %p').lstrip('0')
                horario_info = f" ({entrada_str} - {salida_str})"
            else:
                horario_info = ""
            
            pdf.cell(0, 8, f"{i}. {registro['dia']} ({fecha_dia_str}): {registro['descripcion']}{horario_info}", new_x="LMARGIN", new_y="NEXT")
            if registro['recargo'] > 0:
                pdf.cell(0, 8, f"   + Recargo aplicado: ${registro['recargo']:,.0f}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        
        # CORRECCIÓN: pdf.output() ya retorna bytes, no necesita encode
        return pdf.output()
        
    except Exception as e:
        st.error(f"Error generando PDF: {e}")
        return None

def obtener_nombre_pdf(lunes_semana, domingo_semana):
    """Genera el nombre del PDF con el formato solicitado"""
    return f"Salary_sem_{lunes_semana.strftime('%d_%m_%y')}_to_{domingo_semana.strftime('%d_%m_%y')}.pdf"

def setup_google_sheets():
    """Configura la conexión con Google Sheets"""
    if not SHEETS_AVAILABLE:
        return None
    
    try:
        if 'google_sheets' not in st.secrets:
            st.error("❌ No se encontraron las credenciales de Google Sheets")
            return None
            
        secrets = st.secrets['google_sheets']
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_info(dict(secrets), scopes=SCOPES)
        client = gspread.authorize(creds)
        
        spreadsheet_name = secrets.get('spreadsheet_name', 'Registro_Salarios_Semanal')
        spreadsheet = client.open(spreadsheet_name)
        
        return spreadsheet
        
    except Exception as e:
        st.error(f"❌ Error conectando a Google Sheets: {e}")
        return None

def guardar_en_google_sheets(spreadsheet, registros_semana, total_semanal, horarios_completos, lunes_semana, domingo_semana):
    """Guarda los datos en Google Sheets con fechas exactas"""
    try:
        fecha_guardado = datetime.datetime.now()
        
        # Crear nombre de la hoja con fecha
        nombre_hoja = f"Semana_{lunes_semana.strftime('%d_%m_%y')}_a_{domingo_semana.strftime('%d_%m_%y')}"
        
        # Limpiar nombre de caracteres inválidos
        nombre_hoja = "".join(c for c in nombre_hoja if c.isalnum() or c in (' ', '_', '-')).rstrip()
        
        # Crear o seleccionar worksheet
        try:
            worksheet = spreadsheet.worksheet(nombre_hoja)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=nombre_hoja, rows="100", cols="20")
        
        # CALCULAR TOTAL DE HORAS TRABAJADAS
        total_minutos_trabajados = sum(registro['minutos_trabajados'] for registro in registros_semana)
        total_horas_formato = formato_horas_minutos(total_minutos_trabajados)
        
        # Preparar datos para Google Sheets
        headers = [
            'Día', 'Fecha', 'Entrada', 'Salida', 'Horas Trabajadas', 
            'Pago Base', 'Recargo', 'Total Día', 'Descripción', 'Sin Trabajo'
        ]
        
        data = [headers]
        
        for i, registro in enumerate(registros_semana):
            # Calcular fecha específica para cada día
            fecha_dia = lunes_semana + timedelta(days=i)
            fecha_dia_str = fecha_dia.strftime('%d/%m/%Y')
            
            # Obtener horarios si existen
            entrada_str = "---"
            salida_str = "---"
            
            if registro['dia'] in horarios_completos and not registro['sin_trabajo']:
                horario = horarios_completos[registro['dia']]
                entrada_str = horario['entrada'].strftime('%I:%M %p').lstrip('0')
                salida_str = horario['salida'].strftime('%I:%M %p').lstrip('0')
            
            fila = [
                registro['dia'],
                fecha_dia_str,
                entrada_str,
                salida_str,
                registro['horas_formato'],  # Usar formato hh:mm en lugar de decimal
                registro['pago_base'],
                registro['recargo'],
                registro['pago_total'],
                registro['descripcion'],
                "Sí" if registro['sin_trabajo'] else "No"
            ]
            data.append(fila)
        
        # Agregar filas de información
        data.append([])  # Fila vacía
        data.append(["TOTAL SEMANAL", "", "", "", "", "", "", total_semanal, "", ""])
        data.append(["TOTAL HORAS TRABAJADAS", "", "", "", total_horas_formato, "", "", "", "", ""])
        data.append([])
        data.append(["Fecha de registro", fecha_guardado.strftime("%d/%m/%Y %H:%M:%S")])
        data.append(["Rango de semana", f"{lunes_semana.strftime('%d/%m/%Y')} - {domingo_semana.strftime('%d/%m/%Y')}"])
        
        # Escribir datos
        worksheet.update('A1', data)
        
        # Aplicar formato básico
        try:
            # Resaltar headers
            worksheet.format('A1:J1', {
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.8},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}
            })
            
            # Resaltar totales
            total_row = len(data) - 4
            worksheet.format(f'A{total_row}:J{total_row}', {
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.5},
                'textFormat': {'bold': True}
            })
            
            total_horas_row = len(data) - 3
            worksheet.format(f'A{total_horas_row}:J{total_horas_row}', {
                'backgroundColor': {'red': 0.8, 'green': 0.95, 'blue': 0.8},
                'textFormat': {'bold': True}
            })
            
        except Exception as format_error:
            st.warning(f"⚠️ No se pudo aplicar formato automático: {format_error}")
        
        return nombre_hoja
        
    except Exception as e:
        st.error(f"❌ Error guardando en Google Sheets: {e}")
        return None

def main():
    # Configuración de la página
    st.set_page_config(
        page_title="Calculadora de Salario",
        page_icon="💰",
        layout="wide"
    )
    
    # Título y descripción
    st.title("💰 Calculadora de Salario Semanal")
    
    # SELECTOR DE SEMANA
    lunes, domingo = selector_semana()
    
    # MOSTRAR REGLAS Y TARIFAS (siempre visible)
    mostrar_reglas_tarifas()
    
    st.markdown("### 📝 Ingresa tus horarios por día")
    
    # Configurar Google Sheets
    spreadsheet = None
    if SHEETS_AVAILABLE:
        spreadsheet = setup_google_sheets()
    
    # Inicializar session state
    if 'registros_semana' not in st.session_state:
        st.session_state.registros_semana = []
    if 'total_semanal' not in st.session_state:
        st.session_state.total_semanal = 0
    if 'pdf_bytes' not in st.session_state:
        st.session_state.pdf_bytes = None
    if 'horarios_completos' not in st.session_state:
        st.session_state.horarios_completos = {}
    if 'google_sheets_guardado' not in st.session_state:
        st.session_state.google_sheets_guardado = False
    
    # FORMULARIO DE HORARIOS (sin formulario para permitir reruns automáticos)
    registros_semana, horarios_completos, limpiar = crear_formulario_horarios(lunes, domingo)
    
    if limpiar:
        st.session_state.registros_semana = []
        st.session_state.total_semanal = 0
        st.session_state.pdf_bytes = None
        st.session_state.horarios_completos = {}
        st.session_state.google_sheets_guardado = False
    
    # Botones de acción (fuera del formulario)
    st.markdown("### 🎯 Acciones")
    col1, col2, col3 = st.columns(3)
    
    # Verificar si los horarios están guardados para habilitar el botón de calcular
    semana_key = f"{lunes.strftime('%Y%m%d')}_{domingo.strftime('%Y%m%d')}"
    horarios_guardados = st.session_state.get(f'horarios_guardados_{semana_key}', False)
    
    with col1:
        if horarios_guardados:
            if st.button("📊 Calcular Salario Semanal", type="primary", use_container_width=True):
                if registros_semana:
                    st.session_state.registros_semana = registros_semana
                    st.session_state.total_semanal = sum(registro['pago_total'] for registro in registros_semana)
                    st.session_state.horarios_completos = horarios_completos
                    st.session_state.google_sheets_guardado = False
                    
                    if PDF_AVAILABLE:
                        st.session_state.pdf_bytes = generar_pdf(registros_semana, st.session_state.total_semanal, horarios_completos, lunes, domingo)
                    st.success("✅ Cálculo completado")
                else:
                    st.warning("⚠️ Primero ingresa los horarios y guarda el formulario")
        else:
            st.button("📊 Calcular Salario Semanal", 
                     use_container_width=True, 
                     disabled=True,
                     help="⚠️ Primero debes guardar los horarios para poder calcular")
    
    with col2:
        if spreadsheet and st.session_state.registros_semana and not st.session_state.google_sheets_guardado:
            if st.button("💾 Guardar en Google Sheets", use_container_width=True):
                with st.spinner("Guardando en Google Sheets..."):
                    nombre_hoja = guardar_en_google_sheets(
                        spreadsheet, 
                        st.session_state.registros_semana, 
                        st.session_state.total_semanal,
                        st.session_state.horarios_completos,
                        lunes,
                        domingo
                    )
                    if nombre_hoja:
                        st.session_state.google_sheets_guardado = True
                        st.success(f"✅ Guardado en Google Sheets: {nombre_hoja}")
        elif st.session_state.google_sheets_guardado:
            st.success("✅ Ya guardado en Google Sheets")
    
    with col3:
        if st.button("🔄 Limpiar Todo", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Mostrar resultados solo después de calcular
    if st.session_state.registros_semana:
        st.markdown("---")
        st.markdown("## 📈 Resumen Semanal Detallado")
        
        total_semanal = st.session_state.total_semanal
        
        # CALCULAR TOTAL DE HORAS TRABAJADAS
        total_minutos_trabajados = sum(registro['minutos_trabajados'] for registro in st.session_state.registros_semana)
        total_horas_formato = formato_horas_minutos(total_minutos_trabajados)
        
        # Mostrar tabla de resultados con fechas
        for i, registro in enumerate(st.session_state.registros_semana):
            fecha_dia = lunes + timedelta(days=i)
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 4])
            
            with col1:
                st.write(f"**{registro['dia']}**")
                st.write(f"*{fecha_dia.strftime('%d/%m/%Y')}*")
            
            with col2:
                if registro['sin_trabajo']:
                    st.write("⏸️ Sin trabajo")
                else:
                    dia = registro['dia']
                    if dia in st.session_state.horarios_completos:
                        entrada = st.session_state.horarios_completos[dia]['entrada']
                        salida = st.session_state.horarios_completos[dia]['salida']
                        entrada_str = entrada.strftime('%I:%M %p').lstrip('0')
                        salida_str = salida.strftime('%I:%M %p').lstrip('0')
                        st.write(f"🕒 {entrada_str} - {salida_str}")
            
            with col3:
                if not registro['sin_trabajo']:
                    st.write(f"⏱️ {registro['horas_formato']}")  # Mostrar formato hh:mm
            
            with col4:
                st.write(f"💰 ${registro['pago_total']:,.0f}")
            
            with col5:
                st.write(registro['descripcion'])
                if registro['recargo'] > 0:
                    st.write(f"*+ Recargo: ${registro['recargo']:,.0f}*")
        
        st.markdown("---")
        
        # Mostrar total semanal CON TOTAL DE HORAS
        col_total1, col_total2 = st.columns(2)
        with col_total1:
            st.success(f"## 🎉 TOTAL SEMANAL: ${total_semanal:,.0f}")
        with col_total2:
            st.success(f"## ⏱️ TOTAL HORAS: {total_horas_formato}")
        
        # Sección para generar PDF
        if PDF_AVAILABLE and st.session_state.pdf_bytes is not None:
            st.markdown("### 📄 Generar Reporte en PDF")
            
            # Crear enlace de descarga con nombre personalizado
            try:
                # Asegurarnos de que son bytes
                if isinstance(st.session_state.pdf_bytes, str):
                    b64_pdf = base64.b64encode(st.session_state.pdf_bytes.encode('latin1')).decode()
                else:
                    b64_pdf = base64.b64encode(st.session_state.pdf_bytes).decode()
                    
                nombre_pdf = obtener_nombre_pdf(lunes, domingo)
                
                st.markdown(
                    f'<a href="data:application/pdf;base64,{b64_pdf}" download="{nombre_pdf}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px; font-size: 16px; font-weight: bold; margin: 10px 0;">📥 DESCARGAR {nombre_pdf}</a>',
                    unsafe_allow_html=True
                )
                
                st.info("""
                ✅ **El PDF incluye:**
                - Reglas y tarifas aplicadas
                - Horarios completos en formato AM/PM
                - Fechas exactas para cada día
                - Horas trabajadas en formato hh:mm
                - Cálculo detallado por día
                - Resumen semanal completo
                - **Total de horas trabajadas en formato hh:mm**
                - Formato profesional para impresión
                """)
            except Exception as e:
                st.error(f"Error preparando PDF para descarga: {e}")

if __name__ == "__main__":
    main()
