from openai import OpenAI
from sqlalchemy.orm import Session
from src.core.config import settings
from src.core.logging import get_logger
from src.models.schemas import Proposition
from src.models.db_models import DBProposition, DBScript

logger = get_logger(__name__)

class TikTokService:
    """
    Service to generate TikTok scripts using OpenAI.
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key:
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)

    def generate_script(self, proposition: Proposition, style: str = "informative", db: Session = None) -> str:
        """
        Generate a TikTok script for a given proposition.
        """
        if not self.client:
            return "Error: OpenAI API Key not configured."
            
        prompt = self._create_prompt(proposition, style)
        
        try:
            logger.info(f"Generating script for: {proposition.title}")
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content creator for TikTok, specializing in Brazilian politics and legislation."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,
                max_tokens=2000
            )
            
            script_content = response.choices[0].message.content
            
            # Save to DB
            if db:
                self._save_to_db(db, proposition, script_content, style)
                
            return script_content
            
        except Exception as e:
            logger.error(f"Error generating script: {e}")
            return f"Error generating script: {str(e)}"

    def _save_to_db(self, db: Session, prop: Proposition, content: str, style: str):
        """Save script to DB, creating the proposition if needed."""
        db_prop = self._get_or_create_proposition(db, prop)
        db_script = DBScript(
            proposition_id=db_prop.id if db_prop else None,
            content=content,
            style=style
        )
        db.add(db_script)
        db.commit()
        db.refresh(db_script)
        return db_script

    def _get_or_create_proposition(self, db: Session, prop: Proposition) -> DBProposition | None:
        if not db:
            return None

        query = db.query(DBProposition)
        db_prop = None
        if prop.link:
            db_prop = query.filter(DBProposition.link == prop.link).first()
        if not db_prop:
            db_prop = query.filter(DBProposition.title == prop.title).first()

        if not db_prop:
            db_prop = DBProposition(
                title=prop.title,
                description=prop.description,
                content=prop.content,
                link=prop.link,
                date=prop.date,
                source=prop.source,
                level=prop.level,
                collection_type=prop.collection_type,
            )
            db.add(db_prop)
            db.commit()
            db.refresh(db_prop)

        return db_prop

    def _create_prompt(self, prop: Proposition, style: str) -> str:
        """Create the prompt for the LLM."""
        return f"""
        Create a viral TikTok script (20-30s) about this legislative update.
        
        CONTEXT:
        - Level: {prop.level}
        - Source: {prop.source}
        - Date: {prop.date}
        
        TITLE: {prop.title}
        DESCRIPTION: {prop.description}
        CONTENT: {prop.content[:1000] if prop.content else 'N/A'}
        
        STYLE: {style}. Use linguagem extremamente simples, como se estivesse explicando para alguém que não acompanha política. 
        - Nada de percentuais, números complicados ou termos jurídicos.
        - Sempre troque números por expressões como "quase todo mundo", "pouca gente", "a maioria".
        - Prefira frases curtas, com no máximo 12 palavras.
        - Evite jargões; se precisar citar algo oficial, traduza em uma frase super direta.
        - Foque primeiro em explicar claramente O QUE o projeto faz, depois em quem gosta e quem não gosta.
        
        IMPARTIALITY RULE:
        - Você deve considerar todos os pontos de vista relevantes e expor cada um de forma neutra,
          para que o cidadão consiga refletir e tirar as próprias conclusões.
        - Estruture sempre algo como: "O projeto propõe X. Quem apoia argumenta Y. Já quem critica
          ressalta Z." Acrescente nuances adicionais quando existirem.
        - Mostre impacto prático para grupos diferentes (ex.: moradores, empreendedores, servidores).
        - Evite adjetivos partidários ou juízo de valor. Cite fontes quando possível.
        
        STRUCTURE (OBRIGATÓRIA E FIXA):
        Produza EXATAMENTE dois blocos:
        
        [SEGMENTO 1 - 0-12s]
        [AUDIO] ... (máx. 55 palavras; termine a ideia dentro do bloco)
        [VISUAL] ... (2 frases sobre cenário, luz, câmera)
        
        [SEGMENTO 2 - 12-24s]
        [AUDIO] ... (máx. 55 palavras; fale algo novo ou conclusão)
        [VISUAL] ... (continuação visual coerente com o primeiro bloco)
        
        - Segmento 1 deve cobrir HOOK + “O que faz” + início do impacto.
        - Segmento 2 deve cobrir impacto restante + pontos de vista + CTA.
        - Nunca deixe o trecho 1 com frase inacabada; cada bloco precisa soar completo sozinho.
        - Sem emojis, sem [VISUAL] vagos. Cite objetos reais (fachada da Câmara, mapa, gráfico, mãos segurando conta, etc).
        - Se precisar mostrar texto na tela, descreva na linha [VISUAL] uma animação curta, sem colocar o texto literal no [AUDIO].
        - Linguagem continua ultra simples (fundamental), com frases curtas.
        """

tiktok_service = TikTokService()
