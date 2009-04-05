module NewJersey
  require File.join(File.dirname(__FILE__), '..', 'rbutils', 'legislation')
  require 'mechanize'
  include Scrapable
  
  
  class Bill
    attr_reader :bill_id, :year, :chamber, :actions, :versions, :sponsors, :session
    attr_writer :legislation
    
    def initialize(bill_id, year, chamber)
      @bill_id = bill_id
      @year = year
      @chamber = chamber
      @versions = []
      @sponsors = []
      @actions = []
      @session = "#{year} to #{year.to_i+1} Legislative Session"
    end
    
    
    def add_versions(version,link)
      @versions << {:version => version,:link => "http://www.njleg.state.nj.us/Bills/#{link}"} 
    end
    
    def add_sponsor(sponsor, type)
      @sponsors << {:sponsor => sponsor,:type => type}
    end
    
    def add_action(date,action)
      @actions << {:action => action,:date => date}
    end
    
    def to_hash
      {
        :bill_state => 'nj',
        :bill_chamber => @chamber,
        :bill_session => @session,
        :bill_id => @bill_id,
        :bill_name => @legislation
      }
    end
  end
  
  
  class NJLegislationSite
    
    def initialize (year, chamber)
      @base_uri = "http://www.njleg.state.nj.us"
      @agent = WWW::Mechanize.new
      @agent.get(@base_uri)
      @billpage = fetch_bill_page() #Initializing the Session for that Year
      @year = year
      @chamber = chamber
    end
    
    def fetch_page_count
      @billpage
    end
    
    def bill_numbers(page=1)
      a_bill_numbers = []
      s_bill_numbers = []
      
      if(@billpage.nil?)
        doc = Hpricot(fetch_bill_page(page).body)
          doc.search("//a[@title='View Detail Bill Information']").each do |bill_element|
            bill_number = (bill_element.inner_html).to_s().slice(/[AS][0-9]{1,10}/)
            get_chamber_from_bill_no(bill_number)=="lower" ? a_bill_numbers << bill_number : s_bill_numbers << bill_number        
          end
        @chamber == "lower" ? a_bill_numbers :  s_bill_numbers
      else
        nil
      end
    end
    
    def fetch_bill(bill_id)
      bill = Bill.new(bill_id,@year,@chamber)
      bdp = Hpricot(fetch_bill_detail_page(bill_id).body) #Fetching Bill Detail Page(bdp) for the bill
      
      #Scraping Legislation
      bdp.search('//td[@bgcolor="#fede7e"]').each do |element|
        element.search('//font[@color="maroon"]').each do |l|
            bill.legislation = (l.inner_html).to_s.strip
        end
      end
      
      #Parsing Sponsors
      sponsor_rows = bdp.search('//table[@width="95%"]').search('//tr')[0].search('//font[@face="Arial, Helvetica, sans-serif"]')
      sponsor_rows.each do |sp|
        sp.inner_html.split(/<br \/>/).each do |spx|
        m =  Hpricot(spx).at("font")
          if !m.nil? 
            sponsor =  m.to_plain_text.split(/\sas\s/)
            #pp m.to_plain_text.split(" as ")
            bill.add_sponsor(sponsor[0].strip,sponsor[1])
          end
        end 
      end
      
      #Parsing actions & versions
      action_rows = bdp.search('//table[@width="95%"]').search('//tr')[3].search('//font')
      actions_version = action_rows[0].inner_html().to_s().split("<br />")
      actions_version.each do |element|
        if(element.include?("<a href"))
          #Parsing Versions - Versions have links, looking up by a href
          version =  element.slice(0..(element.index(/<a href/) - 1)).strip
          link =  Hpricot(element).search('a').last[:href]
          bill.add_versions(version,link)
        elsif (element.include?("<font") || element.empty? )
          # Do Nothing
        else
          #Parsing Actions, seperating datesw
          date = element.strip.slice(0..9).strip
          action = element.gsub(/#{date}/," ").strip
          bill.add_action(date,action)
        end
      end
      bill
    end
    
    private
    
    def bill_db
        case @year
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
    
    def get_chamber_from_bill_no(bill_no)
      bill_no.include?("A") ? "lower" : "upper"
    end
    
    def fetch_bill_page(page=1)
      if !bill_db.nil?
        # Get the options page to the set the appropriate cookies
        puts "Fetching for year #{@year}"
        @agent.post("#{@base_uri}/bills/bills0001.asp","DBNAME" => bill_db)
        @agent.post("#{@base_uri}/bills/BillsByNumber.asp","GoToPage" => page)
      else
        nil
      end
    end
    
    def fetch_bill_detail_page(bill_id)
      !bill_db.nil? ? @agent.post("#{@base_uri}/bills/BillView.asp","BillNumber" => bill_id, "LastSession" => "") : nil
     end
  end
 
  def self.state
    "nj"
  end
  
  def self.scrape_bills(chamber,year)
  njs = NJLegislationSite.new(year,chamber)
    #njs.bill_numbers(year,chamber).each do |bill_no|
      #bill = njs.fetch_bill(bill_no,year,chamber)
      #pp bill
    #end
    njs.bill_numbers.each do |bill_id|
       pp njs.fetch_bill(bill_id)
    end
   
    #puts njs.fetch_page_count(year)
    #raise Scrapable::NoDataForYearError.new(@year, "Year has to be even number between 1996-2008")
  end
end


NewJersey.scrape_bills("upper",2006)