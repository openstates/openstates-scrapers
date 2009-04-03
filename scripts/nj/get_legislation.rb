module NewJersey
  require File.join(File.dirname(__FILE__), '..', 'rbutils', 'legislation')
  require 'mechanize'
  include Scrapable
  
  class Bill
    attr_reader :bill_id, :year, :chamber, :actions, :versions, :sponsors
    attr_writer :legislation
    
    def initialize(bill_id, year, chamber)
      @bill_id = bill_id
      @year = year
      @chamber = chamber
      @versions = []
      @sponsors = []
      @actions = []
    end
    
    def add_versions(version,link)
      @versions << {:version => version,:link => link} 
    end
    
    def add_sponsers(sponsor, type)
      @sponsors << {:sponsor => sponsor,:type => type}
    end
    
    def add_action(date,action)
      @actions << {:action => action,:date => date}
    end
  end
  
  
  class NJLegislationSite
    
    def initialize
      @base_uri = "http://www.njleg.state.nj.us"
      @agent = WWW::Mechanize.new
      @agent.get(@base_uri)
    end
    
    def bill_numbers(year,chamber)
      bp = fetch_bill_page(year) #This page is used for getting total no. of pages
      a_bill_numbers = []
      s_bill_numbers = []
      pages = 2 #Extract Total Pages from Bill Page and store, currenlty testing for 5 Pages
      
      if(!bp.nil?)
        pages.times do |page|
          doc = Hpricot(fetch_bill_page(year,page+1).body)
            doc.search("//a[@title='View Detail Bill Information']").each do |bill_element|
              bill_number = (bill_element.inner_html).to_s().slice(/[AS][0-9]{1,10}/)
              if bill_number.include?("A")
                a_bill_numbers << bill_number
              else
                s_bill_numbers << bill_number
              end         
            end
        end
        return chamber == :lower ? a_bill_numbers :  s_bill_numbers
      else
        nil
      end
    end
    
    def fetch_bill(bill_id,year,chamber)
      bill = Bill.new(bill_id,year,chamber)
      bdp = Hpricot(fetch_bill_detail_page(bill_id,year).body) #Fetching Bill Detail Page(bdp) for the bill
      
      #Scraping Legislation
      bdp.search('//td[@bgcolor="#fede7e"]').each do |element|
        element.search('//font[@color="maroon"]').each do |l|
            bill.legislation = (l.inner_html).to_s.strip
        end
      end
      
      #Scraping actions & versions
      action_rows = bdp.search('//table[@width="95%"]').search('//tr')[3].search('//font')
      actions_version = action_rows[0].inner_html().to_s().split("<br />")
      actions_version.each do |element|
        if(element.include?("<a href"))
           puts "== Element =="
           #puts element.to_s.scan(/[\w]*/)
           e = element.to_s.gsub(/<\/?[^>]*>/, "")
           puts e.gsub(/HTML Format/,"")
           #puts e.gsub(/[HTMLFormat] | [PDFFormat]/,"")
        elsif (element.include?("<font") || element.empty? )
          # 
        else
          date = element.strip.slice(0..9).strip
          action = element.gsub(/#{date}/," ").strip
          bill.add_action(date,action)
        end
      end
      
      
       return bill
    end
    
    private
    
    def get_bill_db(year)
       return case year
          when 1996; "LIS9697"
          when 1998; "LIS9899"
          when 2000; "LIS2000"
          when 2002; "LIS2002"
          when 2004; "LIS2004"
          when 2006; "LIS2006"
          when 2008; "LIS2008"
          else nil
        end
    end
    
    def fetch_bill_page(year, page=1)
      year_db=get_bill_db(year)
      if !year_db.nil?
        # Get the options page to the set the appropriate cookies
        @agent.post("#{@base_uri}/bills/bills0001.asp","DBNAME" => year_db)
        return @agent.post("#{@base_uri}/bills/BillsByNumber.asp","GoToPage" => page)
      else
        raise Scrapable::NoDataForYearError.new(year, "Year has to be even number between 1996-2008")
      end
    end
    
    def fetch_bill_detail_page(bill_id,year)
      #Don't call fetch_bill_page here, even though some code is repeated, avoid calling bills0001.asp again
      year_db=get_bill_db(year)
      if !year_db.nil?
        @agent.post("#{@base_uri}/bills/bills0001.asp","DBNAME" => year_db)
        return @agent.post("#{@base_uri}/bills/BillView.asp","BillNumber" => bill_id, "LastSession" => "")
      else
        raise Scrapable::NoDataForYearError.new(year, "Year has to be even number between 1996-2008")
      end
    end
  end
 
  def self.scrape_bills
  njs = NJLegislationSite.new
   # njs.bill_numbers(2006,:lower).each do |bno|
    #  puts "==  Bill  =="
     # bill = njs.fetch_bill(bno,2006,:lower)
      #pp bill
  #  end
   
  njs.fetch_bill("A13",2006,:lower)
  end
end


NewJersey.scrape_bills