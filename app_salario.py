import streamlit as st
import datetime
from fpdf import FPDF
import base64

def calcular_pago_dia(horas_trabajadas, recargo):
    """Calcula el pago del día según las reglas establecidas"""
    HORA_NORMAL = 15500
    TARIFA_6_HORAS = 100000
    
    if horas_trabajadas == 0:
        return 0, "Dia sin trabajo", 0
    elif horas_trabajadas < 6:
        pago_base = horas_trabajadas * HORA_NORMAL
        return pago_base + recargo, f"Horas normales ({horas_trabajadas:.2f}h)", pago_base
    elif horas_trabajadas == 6:
        return TARIFA_6_HORAS + recargo, "6 horas completas", TARIFA_6_HORAS
    else:
        horas_extra = horas_trabajadas - 6
        pago_base = TARIFA_6_HORAS + (horas_extra * HORA_NORMAL)
        return pago_base + recargo, f"6h + {horas_extra:.2f}h extra", pago_base

def generar_pdf(registros_semana, total_semanal, horarios_completos):
    """Genera un PDF con el reporte detallado incluyendo horas de entrada y salida"""
    
    # Crear PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Título
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'REPORTE DE SALARIO SEMANAL', 0, 1, 'C')
    pdf.ln(5)
    
    # Fecha
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(0, 10, f'Generado el: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
    pdf.ln(10)
    
    # Reglas aplicadas
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'REGLAS APLICADAS:', 0, 1)
    pdf.set_font('Arial', '', 10)
    reglas = [
        "- Menos de 6 horas: Horas x $15,500",
        "- Exactamente 6 horas: $100,000 fijos", 
        "- Mas de 6 horas: $100,000 + (horas extra x $15,500)",
        "- Recargos: Se suman al pago base"
    ]
    
    for regla in reglas:
        pdf.cell(0, 8, regla, 0, 1)
    
    pdf.ln(10)
    
    # Tabla de datos MEJORADA con horas de entrada y salida
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'DETALLE POR DIA:', 0, 1)
    pdf.ln(5)
    
    # Encabezados de tabla MEJORADOS
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(25, 10, 'DIA', 1, 0, 'C')
    pdf.cell(20, 10, 'ENTRADA', 1, 0, 'C')
    pdf.cell(20, 10, 'SALIDA', 1, 0, 'C')
    pdf.cell(20, 10, 'HORAS', 1, 0, 'C')
    pdf.cell(30, 10, 'PAGO BASE', 1, 0, 'C')
    pdf.cell(25, 10, 'RECARGO', 1, 0, 'C')
    pdf.cell(35, 10, 'TOTAL DIA', 1, 1, 'C')
    
    # Datos de la tabla MEJORADOS
    pdf.set_font('Arial', '', 8)
    for registro in registros_semana:
        # Obtener horas de entrada y salida del registro completo
        dia = registro['dia']
        if dia in horarios_completos and not registro['sin_trabajo']:
            entrada_str = horarios_completos[dia]['entrada'].strftime('%H:%M')
            salida_str = horarios_completos[dia]['salida'].strftime('%H:%M')
        else:
            entrada_str = "---"
            salida_str = "---"
        
        pdf.cell(25, 10, registro['dia'][:7], 1, 0, 'C')
        pdf.cell(20, 10, entrada_str, 1, 0, 'C')
        pdf.cell(20, 10, salida_str, 1, 0, 'C')
        pdf.cell(20, 10, f"{registro['horas']:.1f}h", 1, 0, 'C')
        pdf.cell(30, 10, f"${registro['pago_base']:,.0f}", 1, 0, 'C')
        pdf.cell(25, 10, f"${registro['recargo']:,.0f}", 1, 0, 'C')
        pdf.cell(35, 10, f"${registro['pago_total']:,.0f}", 1, 1, 'C')
    
    pdf.ln(10)
    
    # Total
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f'TOTAL SEMANAL: ${total_semanal:,.0f} COP', 0, 1, 'C')
    
    pdf.ln(10)
    
    # Reglas aplicadas por dia (detalle)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'ANALISIS POR DIA:', 0, 1)
    pdf.set_font('Arial', '', 10)
    
    for i, registro in enumerate(registros_semana, 1):
        dia = registro['dia']
        if dia in horarios_completos and not registro['sin_trabajo']:
            entrada_str = horarios_completos[dia]['entrada'].strftime('%H:%M')
            salida_str = horarios_completos[dia]['salida'].strftime('%H:%M')
            horario_info = f" ({entrada_str} - {salida_str})"
        else:
            horario_info = ""
        
        pdf.cell(0, 8, f"{i}. {registro['dia']}: {registro['descripcion']}{horario_info}", 0, 1)
        if registro['recargo'] > 0:
            pdf.cell(0, 8, f"   + Recargo aplicado: ${registro['recargo']:,.0f}", 0, 1)
        pdf.ln(2)
    
    # Guardar PDF en bytes
    return pdf.output(dest='S').encode('latin1')

def main():
    # Configuración de la página
    st.set_page_config(
        page_title="Calculadora de Salario",
        page_icon="💰",
        layout="centered"
    )
    
    # Título y descripción
    st.title("💰 Calculadora de Salario Semanal")
    st.markdown("---")
    
    # Información de tarifas
    with st.expander("📊 Ver Tarifas y Reglas"):
        st.markdown("""
        **Tarifas:**
        - Hora normal: $15,500
        - 6 horas completas: $100,000
        - Horas extra: $15,500 c/u
        
        **Recargos disponibles:**
        - $5,000
        - $10,000  
        - $40,000
        - $0 (Ninguno)
        """)
    
    st.markdown("### 📅 Ingresa tus horarios por día")
    
    # Definir días de la semana
    dias_semana = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
    
    # Inicializar session state para almacenar datos
    if 'registros_semana' not in st.session_state:
        st.session_state.registros_semana = []
    if 'total_semanal' not in st.session_state:
        st.session_state.total_semanal = 0
    if 'pdf_generado' not in st.session_state:
        st.session_state.pdf_generado = False
    if 'pdf_bytes' not in st.session_state:
        st.session_state.pdf_bytes = None
    if 'horarios_completos' not in st.session_state:
        st.session_state.horarios_completos = {}
    
    # Formulario para cada día
    registros_semana = []
    horarios_completos = {}
    
    for i, dia in enumerate(dias_semana):
        st.markdown(f"#### {dia}")
        
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            # Checkbox para día sin trabajo
            sin_trabajo = st.checkbox(f"Sin trabajo", key=f"sin_trabajo_{i}")
        
        with col2:
            if not sin_trabajo:
                hora_entrada = st.time_input(
                    f"Entrada {dia}",
                    value=datetime.time(8, 0),
                    key=f"entrada_{i}"
                )
            else:
                hora_entrada = datetime.time(0, 0)
        
        with col3:
            if not sin_trabajo:
                hora_salida = st.time_input(
                    f"Salida {dia}", 
                    value=datetime.time(17, 0),
                    key=f"salida_{i}"
                )
            else:
                hora_salida = datetime.time(0, 0)
        
        # Guardar horarios completos para el PDF
        if not sin_trabajo:
            horarios_completos[dia] = {
                'entrada': hora_entrada,
                'salida': hora_salida
            }
        
        # Selector de recargo
        if not sin_trabajo:
            recargo_opciones = {
                "Ninguno": 0,
                "$5,000": 5000,
                "$10,000": 10000,
                "$40,000": 40000
            }
            
            recargo_seleccionado = st.selectbox(
                f"Recargo {dia}",
                options=list(recargo_opciones.keys()),
                key=f"recargo_{i}"
            )
            recargo = recargo_opciones[recargo_seleccionado]
        else:
            recargo = 0
        
        # Calcular horas trabajadas
        if sin_trabajo:
            horas_trabajadas = 0
        else:
            # Convertir tiempos a minutos
            minutos_entrada = hora_entrada.hour * 60 + hora_entrada.minute
            minutos_salida = hora_salida.hour * 60 + hora_salida.minute
            
            # Calcular diferencia
            if minutos_salida >= minutos_entrada:
                minutos_trabajados = minutos_salida - minutos_entrada
            else:
                # Si la salida es del día siguiente
                minutos_trabajados = (24 * 60 - minutos_entrada) + minutos_salida
            
            horas_trabajadas = minutos_trabajados / 60
        
        # Calcular pago del día
        pago_total, descripcion, pago_base = calcular_pago_dia(horas_trabajadas, recargo)
        
        # Guardar registro
        registro = {
            'dia': dia,
            'horas': horas_trabajadas,
            'pago_base': pago_base,
            'pago_total': pago_total,
            'recargo': recargo,
            'descripcion': descripcion,
            'sin_trabajo': sin_trabajo
        }
        registros_semana.append(registro)
    
    # Botón para calcular
    if st.button("🎯 Calcular Salario Semanal", type="primary"):
        st.session_state.registros_semana = registros_semana
        st.session_state.total_semanal = sum(registro['pago_total'] for registro in registros_semana)
        st.session_state.horarios_completos = horarios_completos
        
        # Generar PDF y guardarlo en session state
        try:
            st.session_state.pdf_bytes = generar_pdf(registros_semana, st.session_state.total_semanal, horarios_completos)
            st.session_state.pdf_generado = True
        except Exception as e:
            st.error(f"Error al generar PDF: {e}")
            st.session_state.pdf_generado = False
    
    # Mostrar resultados si existen
    if st.session_state.registros_semana:
        st.markdown("---")
        st.markdown("## 📊 Resumen Semanal")
        
        total_semanal = st.session_state.total_semanal
        
        # Mostrar tabla de resultados MEJORADA con horarios
        st.markdown("### Detalle de Horarios y Pagos")
        for registro in st.session_state.registros_semana:
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 3])
            
            with col1:
                st.write(f"**{registro['dia']}**")
            
            with col2:
                if registro['sin_trabajo']:
                    st.write("⏸️ Sin trabajo")
                else:
                    dia = registro['dia']
                    if dia in st.session_state.horarios_completos:
                        entrada = st.session_state.horarios_completos[dia]['entrada'].strftime('%H:%M')
                        salida = st.session_state.horarios_completos[dia]['salida'].strftime('%H:%M')
                        st.write(f"🕒 {entrada} - {salida}")
                    else:
                        st.write(f"⏰ {registro['horas']:.2f}h")
            
            with col3:
                if not registro['sin_trabajo']:
                    st.write(f"⏱️ {registro['horas']:.2f}h")
            
            with col4:
                st.write(f"💰 ${registro['pago_total']:,.0f}")
            
            with col5:
                st.write(registro['descripcion'])
        
        st.markdown("---")
        
        # Mostrar total semanal
        st.success(f"## 🎉 TOTAL SEMANAL: ${total_semanal:,.0f}")
        
        # Sección para generar PDF
        st.markdown("---")
        st.markdown("### 📄 Generar Reporte en PDF")
        
        if st.session_state.pdf_generado and st.session_state.pdf_bytes is not None:
            # Crear enlace de descarga
            b64_pdf = base64.b64encode(st.session_state.pdf_bytes).decode()
            
            # Botón de descarga
            st.markdown(
                f'<a href="data:application/pdf;base64,{b64_pdf}" download="reporte_salario_semanal.pdf" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px; font-size: 16px; font-weight: bold;">📥 DESCARGAR REPORTE PDF</a>',
                unsafe_allow_html=True
            )
            
            st.info("""
            ✅ **El PDF incluye:**
            - Horarios de entrada y salida por día
            - Horas trabajadas
            - Pago base y recargos
            - Total por día y semanal
            - Análisis detallado de las reglas aplicadas
            """)
        else:
            st.warning("⚠️ No se pudo generar el PDF. Intenta calcular nuevamente.")
        
        # Botón para reiniciar
        if st.button("🔄 Calcular Nuevamente"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Información adicional
    st.markdown("---")
    st.markdown("""
    ### 💡 Tips:
    - Marca "Sin trabajo" para dias libres
    - Los recargos se suman al pago base
    - Las horas se calculan automaticamente
    - El PDF incluye horarios completos de entrada y salida
    """)

if __name__ == "__main__":
    main()